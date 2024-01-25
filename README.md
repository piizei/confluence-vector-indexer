# Create vector indexes for confluence

## Quick intro

### What can I use this for?

The indexer is a component in a Retrieval Augmented Generation (RAG) application. One example of such application is a chatbot that can answer questions from confluence.
The indexer creates a vector index of confluence pages. This vector index is used from the chatbot to find the most relevant pages for the question.

You don't neccessarily need anything else to build a working chatbot, for example once confluence is indexed to Azure AI Search, you chat with it using the [Azure AI Playground](https://learn.microsoft.com/en-us/azure/ai-services/openai/use-your-data-quickstart?tabs=command-line%2Cpython&pivots=programming-language-studio#chat-playground).

## Usage
This application is intended to be used as a batch run. It should figure out itself what assets need to be updated.
Currently, it supports Azure AI Search, but it should be relatively easy to add other vector databases.

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
| AZURE_SEARCH_ENDPOINT         | the URL of azure ai search                                                               |                        |
| AZURE_SEARCH_KEY=             | Admin key for search. If not specified, should use managed identity.                     |                        |
| AZURE_SEARCH_API_VERSION      | Version of azure ai search api (2023-11-01 or later from rel1.0)                         | 2023-11-01             |
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
| INDEX_ATTACHMENTS             | Index also attachments (See attachment indexing for more info)                           | false                  |

(*) The value of CONFLUENCE_PASSWORD variable is also used for token. 
If password is set for CONFLUENCE_AUTH_METHOD, it uses BASIC authentication, and if Token is set, it sends the password (...token) as Bearer token.
This is functionality of the confluence python SDK.gi

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

## Attachment indexing
The attachment indexing is not enabled by default. You can enable it by setting INDEX_ATTACHMENTS to true.
The supported document types vary by the document indexer. The default implementation is Azure Document Intelligence that [supports PDFs, images, office files (docx, xlsx, pptx), and HTML.](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-retrieval-augumented-generation?view=doc-intel-4.0.0)
Azure AI Document intelligence region must support preview api version 2023-10-31-preview (at this date East US. West US2. West Europe).

# Updates & Upgrades
The Git tags match with the docker-container tags. The releases are not guaranteed to be backward compatible.
Example of breaking change is the update of AI Search API version from preview to GA (rel-0.6 to rel-1.0).
The indexed fields are compatible (but more maybe added). This means the Chat application using the index should not break,
but you would need to reindex the confluence. If it works, no need to update.

# DEV
## Prerequisites
- poetry
- For Azure AI Search, you need to have an Azure account and access to Azure OpenAI

## Testing
Set your personal (or some other equivalent good testing space) to CONFLUENCE_TEST_SPACE and then run
`poetry run pytest`

## Extending
To add your own vector database, just implement the same interface as the Azure AI Search,
and add it to the search.py file.

## TODO
- [ ] Figure out how to remember what removed pages are removed from index
- [ ] Azure AI search skill
- [ ] Add more vector databases / search indexes
- [ ] Figure out how to handle dependencies to various search engines

