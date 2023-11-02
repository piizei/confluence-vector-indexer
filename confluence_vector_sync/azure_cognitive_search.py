import base64
import json
import logging
from datetime import datetime
from typing import List, Dict

import requests
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from dateutil.parser import parse
from langchain.embeddings import OpenAIEmbeddings


class AzureCognitiveSearchWrapper:

    def __init__(self, config):
        self.headers = {'Content-Type': 'application/json', 'api-key': config["azure_search_key"]}
        self.params = {'api-version': config["azure_search_api_version"]}
        self.endpoint = config["azure_search_endpoint"]
        self.index_name = config["azure_search_confluence_index"]
        self.spaces_indexed = []
        self.full_reindex = False
        self.embedder = OpenAIEmbeddings(deployment=config["azure_search_embedding_model"],
                                         chunk_size=1,
                                         )
        self.now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        self.credential = AzureKeyCredential(config["azure_search_key"]) if config[
            "azure_search_key"] else DefaultAzureCredential()
        self.client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)
        self.chunker = None
        self.diagnostics = {"counts": {"create": 0, "update": 0, "remove": 0}}

    def index(self, changeset: Dict[str, List]):
        """List all documents in the index and map to spaces with their pages"""
        # First go through all upserts and update latest_updates for each new space
        # Sor them by date first
        create = []
        update = []
        upserts = sorted(changeset["upsert"], key=lambda x: x["version"]["when"], reverse=True)
        for upsert in upserts:
            space = upsert["space"]["key"]
            if space in self.spaces_indexed:
                continue
            page_id = upsert["id"]
            # Check if document exists (the first chunk)
            try:
                doc = self.client.get_document(key=f"{page_id}_0",
                                               selected_fields=["id", "last_indexed_date", "last_modified_date"])
                last_modified_date = datetime.fromisoformat(doc["last_modified_date"])
                last_indexed_date = datetime.fromisoformat(doc["last_indexed_date"])
                upsert_date = datetime.fromisoformat(upsert["version"]["when"])
                if last_modified_date < upsert_date:
                    update.append(upsert)
                if last_indexed_date > upsert_date and not self.full_reindex:
                    self.spaces_indexed.append(upsert["space"]["key"])
            except Exception as e:
                if e.status_code == 404:
                    create.append(upsert)
                else:
                    raise e
        # remove items in changeset remove
        for item in changeset["remove"]:
            count = self.remove_item(item)
            if count > 0: #The count is number of chunks, not documents
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

    def remove_item(self, item):
        # Get all documents that match the document_id
        results = self.client.search(search_text="*",
                                           filter="document_id eq '" + item["id"] + "'")
        results = list(results)
        to_be_deleted = list(map(lambda x: {'id': x['id']}, results))
        if len(to_be_deleted) > 0:
            self.client.delete_documents(documents=to_be_deleted)
        return len(to_be_deleted)

    def create_item(self, item):
        # Create a new document
        chunks = self.chunker.chunk_page(item)

        for i, chunk in enumerate(chunks):
            document_id = f'{item["id"]}_{i}'
            chunk_text = chunk["text"] if chunk["text"] else "-------"
            last_modified_date = parse(item["version"]["when"]).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            url = f'{item["_links"]["self"].split("rest")[0]}display/{item["space"]["key"]}/{item["_links"]["webui"].split("/")[-1]}'

            document = {
                "id": document_id,
                "document_id": item["id"],
                "space": item["space"]["key"],
                "title": item["title"],
                "chunk": chunk_text,
                "chunkVector": self.embedder.embed_query(chunk_text),
                "last_modified_date": last_modified_date,
                "last_indexed_date": self.now,
                "url": url
            }

        self.client.upload_documents(documents=[document])

    def get_page(self, id: str) -> Dict:
        """Get a page from the search index"""
        resp = requests.post(self.endpoint + "/indexes/" + self.index + "/docs/" + id)

    def get_pages(self, space: str) -> List[Dict]:
        """Get all pages from a space
            :returns: List of Dicts with Id and Last Modified Date
        """

        search_payload = {
            "count": "true",
            "search": "query",
            "select": "",
            "filter": ""
        }

        resp = requests.post(self.endpoint + "/indexes/" + self.index + "/docs/search",
                             data=json.dumps(search_payload), headers=self.headers, params=self.params)

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
                {"name": "title", "type": "Edm.String", "searchable": "true", "retrievable": "true"},
                {"name": "chunk", "type": "Edm.String", "searchable": "true", "retrievable": "true"},
                {"name": "chunkVector", "type": "Collection(Edm.Single)", "searchable": "true", "retrievable": "true",
                 "dimensions": 1536, "vectorSearchConfiguration": "vectorConfig"},
                {"name": "last_modified_date", "type": "Edm.DateTimeOffset", "searchable": "false",
                 "retrievable": "true", "filterable": "true"},
                {"name": "last_indexed_date", "type": "Edm.DateTimeOffset", "searchable": "false",
                 "retrievable": "true", "filterable": "true"},
                {"name": "url", "type": "Edm.String", "searchable": "false", "retrievable": "true"}
            ],
            "vectorSearch": {
                "algorithmConfigurations": [
                    {
                        "name": "vectorConfig",
                        "kind": "hnsw"
                    }
                ]},
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
            logging.error(f'Could not create or update index, error {resp.text}')

    def text_to_base64(self, text: str):
        bytes_data = text.encode('utf-8')
        base64_encoded = base64.b64encode(bytes_data)
        base64_text = base64_encoded.decode('utf-8')
        return base64_text
