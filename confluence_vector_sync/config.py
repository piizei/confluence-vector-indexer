import os
# All the different handlers must be imported so that the dynamic loading works
# Todo: Find a better way to do this
from confluence_vector_sync.gpt_vision import GPTVisionMediaHandler
from confluence_vector_sync.azure_document_intelligence import AzureDocumentIntelligenceMediaHandler


def get_config():
    extra_headers = []
    media_handlers = []
    for key, value in os.environ.items():
        if key.startswith("CONFLUENCE_EXTRA_HEADER_KEY_"):
            extra_headers.append({os.environ[key]: os.environ[key.replace('KEY', 'VALUE')]})
        if key.startswith("MEDIA_HANDLER_KEY_"):
            handler = globals()[os.environ[key.replace('KEY', 'VALUE')]]
            config = os.environ[key.replace('KEY', 'CONFIG')]
            media_types = os.environ[key].split(",")
            for media_type in media_types:
                media_handlers.append({media_type: handler(config)})
    return {
        "search_type": os.getenv("SEARCH_TYPE", "AZURE_COGNITIVE_SEARCH"),
        "azure_search_endpoint": os.getenv("AZURE_SEARCH_ENDPOINT"),
        "azure_search_key": os.getenv("AZURE_SEARCH_KEY"),
        "azure_search_full_reindex": os.getenv("AZURE_SEARCH_FULL_REINDEX", "false").lower() == "true",
        "azure_search_embedding_model": os.getenv("AZURE_SEARCH_EMBEDDING_MODEL", "text-embedding-ada-002"),
        "azure_search_api_version": os.getenv("AZURE_SEARCH_API_VERSION", "2023-11-01"),
        "azure_search_confluence_index": os.getenv("AZURE_SEARCH_CONFLUENCE_INDEX", "confluence"),
        "confluence_url": os.getenv("CONFLUENCE_URL"),
        "confluence_user_name": os.getenv("CONFLUENCE_USER_NAME"),
        "confluence_password": os.getenv("CONFLUENCE_PASSWORD"),
        "confluence_space_filter": os.getenv("CONFLUENCE_SPACE_FILTER", "").split(","),
        "confluence_test_space": os.getenv("CONFLUENCE_TEST_SPACE"),
        "confluence_auth_method": os.getenv("CONFLUENCE_AUTH_METHOD", "PASSWORD"),
        "confluence_extra_headers": extra_headers,
        "index_attachments": os.getenv("INDEX_ATTACHMENTS", "false").lower() == "true",
        "attachment_indexer_type": os.getenv("ATTACHMENT_INDEXER_TYPE", "AZURE_DOCUMENT_INTELLIGENCE"),
        "media_handlers": media_handlers,
    }
