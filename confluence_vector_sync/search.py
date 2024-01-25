from typing import Dict

from confluence_vector_sync.azure_ai_search import AzureAISearchIndexer


def search_indexer_from_config(config: Dict[str, str]):

    match config["search_type"]:
        case "AZURE_COGNITIVE_SEARCH":
            return AzureAISearchIndexer(
                config=config
            )
        case _:
            raise Exception(f'Invalid search type {config["search_type"]} specified in config')
