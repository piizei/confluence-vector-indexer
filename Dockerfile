FROM python:3.11-bookworm

# set work directory
WORKDIR /usr/src/app

# install dependencies
COPY pyproject.toml poetry.lock README.md ./
RUN pip install poetry && \
    poetry config virtualenvs.create false
COPY confluence_vector_sync/ conflu ence_vector_sync/
RUN poetry install
WORKDIR /usr/src/app/confluence_vector_sync

EXPOSE 8080
CMD ["python", "sync.py" ]
