# mini-rag

CLI RAG assistant over `policy.md`: heading-based chunks, local MiniLM embeddings, pgvector cosine top-3, and Ollama grounded answers with citations.

## Setup

1. Start Ollama and pull the chat model:

```bash
ollama serve
ollama pull llama3.2:3b
```

2. Start Postgres 16 with pgvector:

```bash
docker compose up -d
```

3. Apply the schema:

```bash
docker compose exec -T postgres psql -U postgres -d mini_rag < sql/001_init.sql
```

4. Copy env defaults and install Python deps:

```bash
cp .env.example .env
pip install -r requirements.txt
```

`.env` should include `DATABASE_URL`, `EMBEDDING_MODEL=all-MiniLM-L6-v2`, and `OLLAMA_MODEL=llama3.2:3b`.

## Run

Ingest the policy (no Ollama):

```bash
python -m app ingest
```

Ask a question (retrieves top-3 chunks, then calls Ollama):

```bash
python -m app ask "How much can I spend on food each day?"
```

Stdout is JSON: `answer`, `citation` (for example `"1. Meals"`, or `null` on refuse), and `retrieved_chunks` from SQL.

Evaluate all six required questions and write `tests/output.json`:

```bash
python -m app eval
pytest
```
