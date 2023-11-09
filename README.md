# Create vector indexes for confluence
## Introduction
This application is intended to be used as a batch run. It should figure out itself what assets need to be updated.
Currently, it supports Azure Cognitive Search, but it should be relatively easy to add other vector databases.

You need to set plenty of environment variables to make this work. See the .env.example file for a list of them.

It has been tested to work with both Cloud and Server version of confluence. It should in theory also work with the datacenter version (it uses the Confluence python SDK)🤞.

## Running
You can run it with docker:
`docker run --env-file .env ghcr.io/piizei/confluence-vector-indexer:latest`

## Configuration
Check .env.example for values
table of configuration (environment) values

| Name                          | Description                                                                              | Default                |
|-------------------------------|------------------------------------------------------------------------------------------|------------------------|
| AZURE_SEARCH_ENDPOINT         | the URL of azure cognitive search                                                        |                        |
| AZURE_SEARCH_KEY=             | Admin key for search. If not specified, should use managed identity.                     |                        |
| AZURE_SEARCH_API_VERSION      | Version of cognitive search api (2023-07-01-Preview or later)                            | 2023-07-01-Preview     |
| AZURE_SEARCH_CONFLUENCE_INDEX | Index name to be created for confluence.                                                 | confluence             |
| AZURE_SEARCH_EMBEDDING_MODEL  | The deployment name in Azure OpenAi or model name, usually text-embedding-ada-002        | text-embedding-ada-002 |
| AZURE_SEARCH_FULL_REINDEX     | (true, false) Reindex every page (normally just the ones that changed after last index)  | false                  |
| OPENAI_API_KEY                | Key to openai service (no managed identity support as now)                               |                        |
| OPENAI_API_VERSION            | The api version (2023-05-15 for example)                                                 |                        |
| OPENAI_API_TYPE               | azure or none, the none is not tested.                                                   |                        |
| OPENAI_API_BASE               | Azure open-ai service full url (https://myazureopenai.openai.azure.com/)                 |                        |
| CONFLUENCE_URL                | URL for your confluence cloud instance.                                                  |                        |
| CONFLUENCE_USER_NAME          | Your indexer user username                                                               |                        |
| CONFLUENCE_PASSWORD           | Api token created from confluence (not login password)                                   |                        |
| CONFLUENCE_SPACE_FILTER       | Comma separated list of Spaces in confluence (without whitespaces) that will be indexed. |                        |
| CONFLUENCE_TEST_SPACE         | A space against which the integration test runs (your personal space for example)        |                        |
| LOG_LEVEL                     | one of DEBUG, INFO, WARNING                                                              | WARNING                |
| CONFLUENCE_AUTH_METHOD        | one of PASSWORD, TOKEN(*)                                                                | PASSWORD               |

(*) The value of CONFLUENCE_PASSWORD variable is also used for token. 
If password is set for CONFLUENCE_AUTH_METHOD, it uses BASIC authentication, and if Token is set, it sends the password (...token) as Bearer token.
This is functionality of the confluence python SDK.

### Very special configurations
You can add custom headers to the requests to confluence by adding CONFLUENCE_HEADER_XXX variables, where XXX is the number of custom header-value pair.
This is useful if you want for example to use Cloudflare Service Tokens to connect to on-prem confluence server.

Example of using Cloudflare Service Tokens:

| Name                            | Value                   |
|---------------------------------|-------------------------|
| CONFLUENCE_EXTRA_HEADER_KEY_1   | CF-Access-Client-Id     | 
| CONFLUENCE_EXTRA_HEADER_KEY_2   | CF-Access-Client-Secret | 
| CONFLUENCE_EXTRA_HEADER_VALUE_1 | 123.access              |                                                       | 
| CONFLUENCE_EXTRA_HEADER_VALUE_2 | abc123qwertysecret      |


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

