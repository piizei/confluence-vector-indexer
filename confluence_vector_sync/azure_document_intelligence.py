import json
import logging
from typing import List

from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader
from langchain_core.documents import Document


class AzureDocumentIntelligenceMediaHandler:
    api_model = "prebuilt-layout"
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    def __init__(self, json_string_config: str):
        config = json.loads(json_string_config)
        self.api_endpoint = config["ENDPOINT"]
        self.api_key = config["API_KEY"]

    def handle(self, file_path: str) -> List[Document]:
        loader = AzureAIDocumentIntelligenceLoader(
            api_endpoint=self.api_endpoint,
            api_key=self.api_key,
            file_path=file_path,
            api_model=self.api_model
        )
        try:
            documents = loader.load()
        except Exception as e:
            logging.ERROR(f"Error loading document {file_path}: {e}")
            return []

        text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=self.headers_to_split_on)

        docs_string = documents[0].page_content
        return text_splitter.split_text(docs_string)
