from typing import Dict

from confluence_vector_sync.azure_cognitive_search import AzureCognitiveSearchWrapper


def search_from_config(config: Dict[str, str]):

    match config["search_type"]:
        case "AZURE_COGNITIVE_SEARCH":
            return AzureCognitiveSearchWrapper(
                config=config
            )
        case _:
            raise Exception(f'Invalid search type {config["search_type"]} specified in config')
