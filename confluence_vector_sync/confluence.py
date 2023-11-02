from typing import Dict, List

from atlassian import Confluence
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter


class ConfluenceWrapper:
    """Wrapper for Confluence API"""
    space_filter: List[str] = []
    chunk_size = 8000
    chunk_overlap = 200

    def __init__(self, url, username, password):
        self.confluence = Confluence(url=url,
                                     username=username,
                                     password=password)

    def create_space_page_map(self) -> Dict[str, Dict]:
        """Creates a map of spaces with their pages"""
        # Todo: Add pagination, 500 is not much if all users have their space. (pages already have pagination)
        spaces = self.confluence.get_all_spaces(start=0, limit=500, expand=None)["results"]
        if len(self.space_filter) > 0:
            spaces = [space for space in spaces if space["key"] in self.space_filter]
        space_page_map = {}
        for space in spaces:
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
        content = self.confluence.get_page_by_id(page_header["id"], expand="body.storage")["body"]["storage"]["value"]
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


def confluence_from_config(config: Dict[str, str]) -> ConfluenceWrapper:
    return ConfluenceWrapper(url=config["confluence_url"],
                             username=config["confluence_user_name"],
                             password=config["confluence_password"])
