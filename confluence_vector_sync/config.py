from os import environ


def get_config():
    return {
        "search_type": environ.get("SEARCH_TYPE") if environ.get("SEARCH_TYPE") else "AZURE_COGNITIVE_SEARCH",
        "azure_search_endpoint": environ.get("AZURE_SEARCH_ENDPOINT"),
        "azure_search_key": environ.get("AZURE_SEARCH_KEY"),
        "azure_search_embedding_model": environ.get("AZURE_SEARCH_EMBEDDING_MODEL"),
        "azure_search_api_version": environ.get("AZURE_SEARCH_API_VERSION"),
        "azure_search_confluence_index": environ.get("AZURE_SEARCH_CONFLUENCE_INDEX") if environ.get("AZURE_SEARCH_CONFLUENCE_INDEX") else "confluence",
        "confluence_url": environ.get("CONFLUENCE_URL"),
        "confluence_user_name": environ.get("CONFLUENCE_USER_NAME"),
        "confluence_password": environ.get("CONFLUENCE_PASSWORD"),
        "confluence_space_filter": environ.get("CONFLUENCE_SPACE_FILTER").split(",") if environ.get("CONFLUENCE_SPACE_FILTER") else [],
        "confluence_test_space": environ.get("CONFLUENCE_TEST_SPACE"),
    }
