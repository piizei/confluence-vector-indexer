import logging
import os
from typing import Dict

from dotenv import load_dotenv

from confluence_vector_sync import otel
from confluence_vector_sync.attachment_loader import AttachmentLoader
from confluence_vector_sync.config import get_config
from confluence_vector_sync.confluence import confluence_from_config
from confluence_vector_sync.search import search_indexer_from_config


def sync(config: Dict[str, str] = None, confluence=None, search=None):
    load_dotenv()
    otel.setup()
    logging.getLogger().setLevel(level=os.getenv('LOG_LEVEL', 'WARNING').upper())
    logging.info("Indexing started")
    if not config:
        config = get_config()
    if not confluence:
        confluence = confluence_from_config(config)

    if not search:
        search = search_indexer_from_config(config)
    if config["index_attachments"]:
        search.attachment_loader = AttachmentLoader(config["media_handlers"])
        confluence.handle_attachments = True
    confluence.space_filter = config["confluence_space_filter"]
    page_model = confluence.create_space_page_map()
    current = [page for p in page_model for page in page_model[p]["pages"] if
               page["status"] not in {"archived", "trashed"}]
    archived = [page for p in page_model for page in page_model[p]["pages"] if
                page["status"] in {"archived", "trashed", "deleted"}]
    # Create model of documents in search-index for all included confluence spaces
    search.create_or_update_index()
    search.confluence = confluence

    search.index(changeset={"upsert": current, "remove": archived})
    if config["index_attachments"]:
        for space in confluence.space_filter:
            logging.info("Purging deleted attachments from index for space %s", space)
            search.purge_attachments(space)
    logging.info("Indexing complete")
    logging.debug(search.diagnostics)
    return search.diagnostics


# main
if __name__ == "__main__":
    print(sync())
