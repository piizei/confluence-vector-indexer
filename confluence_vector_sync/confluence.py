import json
from typing import Dict, List
import os
from datetime import datetime, timezone
import tempfile
import requests
import urllib3
from atlassian import Confluence
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter


class ConfluenceWrapper:
    """Wrapper for Confluence API"""
    space_filter: List[str] = []
    chunk_size = 2000
    chunk_overlap = 500
    handle_attachments = False
    datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'

    def __init__(self, url, username, password, auth_method="PASSWORD", extra_headers=[], ignore_ssl=False):
        session = requests.Session()
        if ignore_ssl:
            session.verify = False
            urllib3.disable_warnings()
            print("SSL verification disabled")
        for extra in extra_headers:
            session.headers.update(extra)
        if auth_method == "PASSWORD":
            self.confluence = Confluence(url=url,
                                         username=username,
                                         password=password,
                                         session=session)
        else:
            self.confluence = Confluence(url=url,
                                         username=username,
                                         token=password,
                                         session=session)
        self.session = session

    def create_space_page_map(self) -> Dict[str, Dict]:
        """Creates a map of spaces with their pages"""
        results = []
        i = 0
        if len(self.space_filter) > 0:
            for space_key in self.space_filter:
                result = self.confluence.get_space(space_key=space_key)
                results.append(result)
        else:
            while True:
                iter_results = self.confluence.get_all_spaces(space_type='global', start=i, limit=i + 100, expand=None)[
                    "results"]
                if len(iter_results) == 0:
                    break
                results.extend(iter_results)
                i += 100

        space_page_map = {}
        for space in results:
            pages = self.get_pages(space["key"])
            for page in pages:
                if 'version' in page:
                    page["last_modified"] = datetime.fromisoformat(page["version"]["when"])
                if self.handle_attachments:
                    try:
                        attachments_container = self.confluence.get_attachments_from_content(page_id=page["id"])
                    except:
                        attachments_container = None
                    if attachments_container and attachments_container["size"] > 0:
                        page["attachments"] = attachments_container["results"]
                        for result in attachments_container["results"]:
                            if "_links" in result and "download" in result["_links"]:
                                attachment_last_modified = get_last_modified_attachment(result)
                                if attachment_last_modified > page["last_modified"]:
                                    page["last_modified"] = attachment_last_modified

            space_page_map[space["key"]] = {
                "pages": pages,
            }
        return space_page_map

    def get_pages(self, space_key: str) -> List[Dict]:
        results = []
        i = 0
        while True:
            iter_results = self.confluence.get_all_pages_from_space(space_key, start=i, limit=i + 100, status='any',
                                                                    expand='history,space,version', content_type='page')
            if len(iter_results) == 0:
                break
            results.extend(iter_results)
            i += 100
        return results

    def chunk_page(self, page_header: Dict) -> List[Dict]:
        """Chunks a page into smaller pieces"""
        try:
            content = self.confluence.get_page_by_id(page_header["id"], expand="body.storage")["body"]["storage"][
                "value"]
            soup = BeautifulSoup(content, 'html.parser').get_text()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            chunks = text_splitter.split_text(soup)
            doc_chunks = []
            for i, chunk in enumerate(chunks):
                doc_chunks.append({"text": chunk, "chunk": i})
            return doc_chunks
        except:
            return []

    def get_attachment_page_url(self, attachment: Dict) -> str:
        return self.confluence.url + attachment["_links"]["download"]

    def get_attachment_by_id(self, attachment_id: str) -> str:
        try:
            url = self.confluence.url + "api/v2/attachments/" + attachment_id
            request = self.session.get(url, stream=True)
            if request.status_code == 200:
                item = json.loads(request.text)
                if item["status"] == "trashed":
                    return None
                return item
            else:
                return None
        except:
            return None

    def download_to_tempfile(self, attachment):
        url = self.get_attachment_page_url(attachment)
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Send a HTTP request to the URL
            response = self.session.get(url, stream=True)

            # Check if the request is successful
            if response.status_code == 200:
                # Write the content to the temporary file
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        temp_file.write(chunk)

            # Return the path of the temporary file
            return temp_file.name


def get_last_modified_attachment(attachment) -> datetime:
    return datetime.fromtimestamp(int(attachment["_links"]["download"]
                                      .split("modificationDate=")[1]
                                      .split("&")[0]) / 1000,
                                  tz=timezone.utc)


def confluence_from_config(config: Dict[str, str]) -> ConfluenceWrapper:
    """Creates a ConfluenceWrapper from a config"""
    return ConfluenceWrapper(url=config["confluence_url"],
                             username=config["confluence_user_name"],
                             password=config["confluence_password"],
                             auth_method=config["confluence_auth_method"],
                             extra_headers=config["confluence_extra_headers"],
                             ignore_ssl=config["ignore_confluence_cert"])
