from typing import Dict, List

import requests
from atlassian import Confluence
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter


class ConfluenceWrapper:
    """Wrapper for Confluence API"""
    space_filter: List[str] = []
    chunk_size = 8000
    chunk_overlap = 200

    def __init__(self, url, username, password, auth_method="PASSWORD", extra_headers=[]):
        session = requests.Session()
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
                iter_results = self.confluence.get_all_spaces(space_type='global', start=i, limit=i+100, expand=None)[
                    "results"]
                if len(iter_results) == 0:
                    break
                results.extend(iter_results)
                i += 100

        space_page_map = {}
        for space in results:
            space_page_map[space["key"]] = {
                "pages": self.get_pages(space["key"])
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


def confluence_from_config(config: Dict[str, str]) -> ConfluenceWrapper:
    """Creates a ConfluenceWrapper from a config"""
    return ConfluenceWrapper(url=config["confluence_url"],
                             username=config["confluence_user_name"],
                             password=config["confluence_password"],
                             auth_method=config["confluence_auth_method"],
                             extra_headers=config["confluence_extra_headers"])
