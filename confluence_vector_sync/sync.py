import logging
import os

from dotenv import load_dotenv

from confluence_vector_sync import otel
from confluence_vector_sync.config import get_config
from confluence_vector_sync.confluence import confluence_from_config
from confluence_vector_sync.search import search_from_config
def sync():
    load_dotenv()
    otel.setup()
    logging.getLogger().setLevel(level=os.getenv('LOG_LEVEL', 'WARNING').upper())
    logging.info("Indexing started")
    config = get_config()
    confluence = confluence_from_config(config)
    confluence.space_filter = config["confluence_space_filter"]
    page_model = confluence.create_space_page_map()
    current = [page for p in page_model for page in page_model[p]["pages"] if
               page["status"] not in {"archived", "trashed"}]
    archived = [page for p in page_model for page in page_model[p]["pages"] if
                page["status"] in {"archived", "trashed", "deleted"}]
    # Create model of documents in search-index for all included confluence spaces
    search = search_from_config(config)
    search.chunker = confluence
    search.create_or_update_index()
    search.index(changeset={"upsert": current, "remove": archived})
    logging.info("Indexing complete")
    logging.debug(search.diagnostics)
    return search.diagnostics

# main
if __name__ == "__main__":
    print(sync())
