import base64
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict

import requests
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from dateutil.parser import parse
from langchain.embeddings import OpenAIEmbeddings

from confluence_vector_sync.confluence import get_last_modified_attachment


class AzureAISearchIndexer:
    datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'

    def __init__(self, config):
        self.attachment_cache = {}
        self.diagnostics = None
        self.headers = {'Content-Type': 'application/json', 'api-key': config["azure_search_key"]}
        self.params = {'api-version': config["azure_search_api_version"]}
        self.endpoint = config["azure_search_endpoint"]
        self.index_name = config["azure_search_confluence_index"]
        self.spaces_indexed = []
        self.full_reindex = config["azure_search_full_reindex"]
        self.embedder = OpenAIEmbeddings(deployment=config["azure_search_embedding_model"],
                                         chunk_size=1,
                                         )
        self.now = datetime.utcnow().strftime(self.datetime_format)
        self.credential = AzureKeyCredential(config["azure_search_key"]) if config[
            "azure_search_key"] else DefaultAzureCredential()
        self.client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)
        self.confluence = None
        self.reset()

    def index(self, changeset: Dict[str, List]):
        """List all documents in the index and map to spaces with their pages"""
        # First go through all upserts and update latest_updates for each new space
        # Sor them by date first
        create = []
        update = []
        upserts = sorted(changeset["upsert"], key=lambda x: x["last_modified"], reverse=True)
        for upsert in upserts:
            space = upsert["space"]["key"]
            if space in self.spaces_indexed:
                continue
            page_id = upsert["id"]
            # Check if document exists (the first chunk)
            last_indexed_date, last_modified_date_in_index = self.get_indexing_metadata(page_id)
            if last_indexed_date is None:
                create.append(upsert)
            else:
                modified_in_confluence = upsert["last_modified"]
                if last_modified_date_in_index < modified_in_confluence or self.full_reindex:
                    update.append(upsert)
                if last_indexed_date > modified_in_confluence and not self.full_reindex:
                    self.spaces_indexed.append(upsert["space"]["key"])

        # remove items in changeset remove
        for item in changeset["remove"]:
            count = self.remove_item(item)
            if count > 0:  # The count is number of chunks, not documents
                self.diagnostics["counts"]["remove"] += 1
        # remove items that need to be updated ->
        # document is split in multiple search entries and we dont know how its going to chuck this time ->
        # easier to remove existing chunks and reindex
        for item in update:
            self.diagnostics["counts"]["update"] += 1
            self.remove_item(item)
            self.create_item(item)
        # create new items
        for item in create:
            self.diagnostics["counts"]["create"] += 1
            self.create_item(item)

    def get_indexing_metadata(self, page_id):
        # not found, set olden times
        last_modified_date_in_index = datetime(1900, 1, 1, 1, 1, tzinfo=timezone.utc)
        last_indexed_date = None
        try:
            doc = self.client.get_document(key=f"{page_id}_0",
                                            selected_fields=["id", "last_indexed_date", "last_modified_date"])
            last_modified_date_in_index = datetime.fromisoformat(doc["last_modified_date"])
            last_indexed_date = datetime.fromisoformat(doc["last_indexed_date"])
        except:
            # not found in ai-search
            pass
        return last_indexed_date, last_modified_date_in_index

    def remove_item(self, item):
        # Get all documents that match the document_id
        results = list(self.client.search(search_text="*",
                                          filter="document_id eq '" + item["id"] + "'"))
        attachment_results = list(self.client.search(search_text="*",
                                                     filter="attachment_page_id eq '" + item["id"] + "'"))
        results.extend(attachment_results)
        to_be_deleted = list(map(lambda x: {'id': x['id']}, results))
        if len(to_be_deleted) > 0:
            self.client.delete_documents(documents=to_be_deleted)
        return len(to_be_deleted)

    def create_item(self, item):
        # Handle attachments
        docs = []
        for attachment in item.get("attachments", []):
            self.add_to_attachment_cache(item["space"]["key"], attachment)
            create = False
            # check if we can handle it, otherwise don't download
            if self.attachment_loader.can_handle(attachment["metadata"]["mediaType"]):
                # Check if attachment has been modified since last index
                last_indexed_date, last_modified_date_in_index = self.get_indexing_metadata(attachment["id"])
                if last_indexed_date is None:
                    create = True

                last_modified_in_confluence = get_last_modified_attachment(attachment)
                if last_modified_date_in_index < last_modified_in_confluence:
                    tmp_file = self.confluence.download_to_tempfile(attachment)
                    attachment_chunks = self.attachment_loader.load(tmp_file, attachment["metadata"]["mediaType"])
                    if attachment_chunks:
                        docs.extend(self.chunks_to_documents(attachment_chunks, item,
                                                             attachment=attachment))
                        if create:
                            self.diagnostics["counts"]["attachment-create"] += 1
                        else:
                            self.diagnostics["counts"]["attachment-update"] += 1
        # Create a new document
        page_chunks = self.confluence.chunk_page(item)
        docs.extend(self.chunks_to_documents(page_chunks, item))
        try:
            for doc in docs:
                resp = self.client.upload_documents(documents=[doc])
                if not resp[0].succeeded:
                    logging.warning(f"Could not index document {doc['url']} to Azure Search: {resp[0].errors}")
        except Exception as e:
            logging.warning(f"Could not index documents to Azure Search: {e}")

    def chunks_to_documents(self,
                            chunks: List[Dict],
                            item: Dict,
                            attachment: Dict = None
                            ) -> List[Dict]:
        docs = []
        attachment_page_url = ""
        attachment_page_id = ""
        title_vector = []
        title = item["title"]
        item_type = "page"
        url = f'{item["_links"]["self"].split("rest")[0]}display/{item["space"]["key"]}/{item["_links"]["webui"].split("/")[-1]}'
        item_id = item["id"]

        if attachment is None:
            last_modified_date = item["last_modified"].strftime(self.datetime_format)
            title_vector = self.embedder.embed_query(item["title"])
        else:
            item_type = "attachment:" + attachment["metadata"]["mediaType"]
            attachment_page_url = url
            attachment_page_id = item_id
            url = self.confluence.get_attachment_page_url(attachment)
            item_id = attachment["id"]
            title = attachment["title"]
            if "comment" in attachment["metadata"]:
                title = title + " - " + attachment["metadata"]["comment"]
            epoch = get_last_modified_attachment(attachment)
            last_modified_date = epoch.strftime(self.datetime_format)
        for i, chunk in enumerate(chunks):
            document_id = f'{item_id}_{i}'
            # Todo: harmonize the text-field in Document
            if attachment is None:
                chunk_text = chunk["text"] if chunk["text"] else "-------"
            else:
                chunk_text = chunk.page_content
            docs.append({
                "id": document_id,
                "document_id": item_id,
                "space": item["space"]["key"],
                "item_type": item_type,
                "attachment_page_url": attachment_page_url,
                "attachment_page_id": attachment_page_id,
                "title": title,
                "titleVector": title_vector,
                "chunk": chunk_text,
                "chunkVector": self.embedder.embed_query(chunk_text),
                "last_modified_date": last_modified_date,
                "last_indexed_date": self.now,
                "url": url
            })
        return docs


    def add_to_attachment_cache(self, space: str, attachment: Dict):
        if not space in self.attachment_cache:
            self.attachment_cache[space] = []
        self.attachment_cache[space].append(attachment["id"])

    def purge_attachments(self, space):
        results = list(self.client.search(search_text="*", filter=f"space eq '{space}' and item_type ne 'page'"))
        ids = [result['id'] for result in results]

        # Filter out all attachments that are not in the cache
        if space in self.attachment_cache:
            ids = [id for id in ids if id.split("_")[0] not in self.attachment_cache[space]]

        # Check that the remaining items are in confluence
        ids = [id for id in ids if self.confluence.get_attachment_by_id(id.split("_")[0]) is None]

        if ids:
            to_be_deleted = [{'id': id} for id in ids]
            self.client.delete_documents(documents=to_be_deleted)
            self.diagnostics["counts"]["remove"] += len(ids)

    def create_or_update_index(self):
        """Create or update the index with the latest schema
            the operation is idempotent and can be invoked multiple times without any side effects
        """
        schema = {
            "name": self.index_name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": "true", "searchable": "false", "retrievable": "true",
                 "filterable": "true"},
                {"name": "document_id", "type": "Edm.String", "key": "false", "searchable": "false",
                 "retrievable": "true", "filterable": "true"},
                {"name": "space", "type": "Edm.String", "searchable": "true", "retrievable": "true",
                 "filterable": "true"},
                {"name": "attachment_page_url", "type": "Edm.String", "searchable": "false", "retrievable": "true",
                 "filterable": "false"},
                {"name": "attachment_page_id", "type": "Edm.String", "searchable": "true", "retrievable": "true",
                 "filterable": "true"},
                {"name": "item_type", "type": "Edm.String", "searchable": "false", "retrievable": "true",
                 "filterable": "true"},
                {"name": "title", "type": "Edm.String", "searchable": "true", "retrievable": "true"},
                {"name": "titleVector", "type": "Collection(Edm.Single)", "searchable": "true", "retrievable": "true",
                 "dimensions": 1536, "vectorSearchProfile": "default-vector-profile"},
                {"name": "chunk", "type": "Edm.String", "searchable": "true", "retrievable": "true"},
                {"name": "chunkVector", "type": "Collection(Edm.Single)", "searchable": "true", "retrievable": "true",
                 "dimensions": 1536, "vectorSearchProfile": "default-vector-profile"},
                {"name": "last_modified_date", "type": "Edm.DateTimeOffset", "searchable": "false",
                 "retrievable": "true", "filterable": "true"},
                {"name": "last_indexed_date", "type": "Edm.DateTimeOffset", "searchable": "false",
                 "retrievable": "true", "filterable": "true"},
                {"name": "url", "type": "Edm.String", "searchable": "false", "retrievable": "true"}
            ],
            "vectorSearch": {
                "algorithms": [
                    {
                        "name": "hnsw-config-1",
                        "kind": "hnsw"
                    }],
                "profiles": [
                    {
                        "name": "default-vector-profile",
                        "algorithm": "hnsw-config-1"
                    }
                ]
            },
            "semantic": {
                "configurations": [
                    {
                        "name": "my-semantic-config",
                        "prioritizedFields": {
                            "titleField": {
                                "fieldName": "title"
                            },
                            "prioritizedContentFields": [
                                {
                                    "fieldName": "chunk"
                                }
                            ],
                            "prioritizedKeywordsFields": []
                        }
                    }
                ]
            }
        }
        resp = requests.put(self.endpoint + "/indexes/" + self.index_name, data=json.dumps(schema),
                            headers=self.headers, params=self.params)

        if resp.status_code > 299:
            print(f'Could not create or update index, error {resp.text}')
            logging.error(f'Could not create or update index, error {resp.text}')
            exit(-1)

    def drop_index(self):
        resp = requests.delete(self.endpoint + "/indexes/" + self.index_name, headers=self.headers, params=self.params)

    def text_to_base64(self, text: str):
        bytes_data = text.encode('utf-8')
        base64_encoded = base64.b64encode(bytes_data)
        base64_text = base64_encoded.decode('utf-8')
        return base64_text

    def reset(self):
        self.spaces_indexed = []
        self.diagnostics = {"counts": {"create": 0,
                                       "update": 0,
                                       "remove": 0,
                                       "attachment-create": 0,
                                       "attachment-update": 0}
                            }
