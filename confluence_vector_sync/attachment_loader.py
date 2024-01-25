import logging
from typing import List

from langchain_core.documents import Document


class AttachmentLoader:
    """Index different attachment mediatypes and the handler configuration."""

    handlers = {}

    def __init__(self, media_handlers: List):
        # It's a list of key-value pair dicts, but we want a single dict
        self.handlers = {k: v for d in media_handlers for k, v in d.items()}

    def load(self, file_path: str, media_type: str) -> List[Document]:
        """Index attached file with the appropriate handler."""

        if self.can_handle(media_type):
            return self.handlers[media_type].handle(file_path)
        else:
            logging.warning(f"No handler for mediatype {media_type} found")

    def can_handle(self, media_type: str) -> bool:
        """Check if a handler for the given mediatype exists."""

        return media_type in self.handlers
