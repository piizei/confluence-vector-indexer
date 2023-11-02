# Create vector indexes for confluence
## Introduction
This application is intended to be used as a batch run. It should figure out itself what assets need to be updated.
Currently, it supports Azure Cognitive Search, but it should be relatively easy to add other vector databases.

You need to set plenty of environment variables to make this work. See the .env.example file for a list of them.

## Running
You can run it with docker:
`docker run --env-file .env ghcr.io/piizei/confluence-vector-indexer:latest`

# DEV
## Prerequisites
- poetry
- For Azure Cognitive Search, you need to have an Azure account and access to Azure OpenAI

## Testing
Set your personal (or some other equivalent good testing space) to CONFLUENCE_TEST_SPACE and then run
`poetry run pytest`

## Extending
To add your own vector database, just implement the same interface as the AzureCognitiveSearch,
and add it to the search.py file.

## TODO
- [ ] Figure out how to remember what removed pages are removed from index
- [ ] Cognitive search skill
- [ ] Add more vector databases / search indexes
- [ ] Figure out how to handle dependencies to various search engines

