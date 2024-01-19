import json
from typing import List

from langchain.chat_models import AzureChatOpenAI, ChatOpenAI
from langchain_core.documents import Document


class GPTVisionMediaHandler:

    def __init__(self, json_string_config: str):
        config = json.loads(json_string_config)
        if config["OPENAI_API_TYPE"] == "AZURE":
            llm = AzureChatOpenAI(
                openai_api_version=config["OPENAI_API_VERSION"],
                azure_deployment=config["DEPLOYMENT"],
                azure_openai_api_key=config["OPENAI_API_KEY"],
                azure_openai_api_endpoint=config["OPENAI_API_BASE"],
            )
        else:
            # Todo: No idea if this works, only tested with Azure OpenAI -\_(o.o)_/-
            llm = ChatOpenAI(
                openai_api_key=config["OPENAI_API_KEY"],
                openai_api_base=config["OPENAI_API_BASE"],
                openai_api_version=config["OPENAI_API_VERSION"],
            )
        self.llm = llm

    def handle(self, file_path: str) -> List[Document]:
        print("Not implemented yet")
        return []
