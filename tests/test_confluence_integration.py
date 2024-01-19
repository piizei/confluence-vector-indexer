import logging
import random
import string
import time

import pytest

from confluence_vector_sync.config import get_config
from confluence_vector_sync.confluence import confluence_from_config
from dotenv import load_dotenv

from confluence_vector_sync.search import search_indexer_from_config
from confluence_vector_sync.sync import sync


@pytest.fixture
def config():
    load_dotenv()
    config = get_config()
    config["confluence_space_filter"] = [config["confluence_test_space"]]
    config["azure_search_confluence_index"] = config["azure_search_confluence_index"] + "_" + get_random_string()
    return config


@pytest.fixture
def confluence(config):
    confluence = confluence_from_config(config)
    return confluence


@pytest.fixture
def search(config, confluence):
    search = search_indexer_from_config(config)
    search.confluence = confluence
    yield search
    search.drop_index()


def test_crud(search, confluence, config):
    # First run on fresh index
    diagnostics = sync(config, confluence, search)
    assert_diagnostics(diagnostics, count_create=None)
    search.reset()
    # Run the indexer once, and then assert that nothing changed
    # If something changed on wiki, then it got indexed and next time the test should work again :)
    diagnostics = sync(config, confluence, search)
    assert_diagnostics(diagnostics)
    search.reset()
    test_page = confluence.confluence.create_page(config["confluence_test_space"], "Test page", "<p>Test page</p>")
    diagnostics = sync(config, confluence, search)
    assert_diagnostics(diagnostics, count_create=1)
    search.reset()
    # Check that it was actually put into search index
    # Note that this only works with Azure Cognitive Search as it's using it's client directly
    # Todo: refactor if other search engines are added
    # Also sleep a bit before searching, it takes few seconds for the index to update
    time.sleep(5)
    search.client.get_document(key=f"{test_page['id']}_0", selected_fields=["id"])
    # Update
    random_str = get_random_string()
    confluence.confluence.update_page(test_page["id"], f"<p>Test page updated {random_str}</p>")
    diagnostics = sync(config, confluence, search)
    assert_diagnostics(diagnostics, count_update=1)
    search.reset()
    time.sleep(5)
    doc = search.client.search(search_text=random_str,
                               include_total_count=True,
                               filter=f"document_id eq '{test_page['id']}'")
    assert doc.get_count() == 1
    confluence.confluence.remove_page(test_page["id"])
    diagnostics = sync(config, confluence, search)
    assert_diagnostics(diagnostics, count_remove=1)
    search.reset()
    try:
        doc = search.client.get_document(key=f"{test_page['id']}_0")
        assert False  # Should not get here
    except Exception as e:
        assert e.status_code == 404


def assert_diagnostics(diagnostics, count_create=0, count_update=0, count_remove=0):
    print("Diagnostics: ", diagnostics)
    if count_create is not None:
        assert diagnostics["counts"]["create"] == count_create
    assert diagnostics["counts"]["update"] == count_update
    assert diagnostics["counts"]["remove"] == count_remove


def get_random_string():
    return ''.join(random.choice(string.ascii_lowercase) for i in range(5))
