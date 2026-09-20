# Mini-RAG Project on Policy with 6 Sections

## Setup

```bash
ollama serve
```

In another terminal:

```bash
ollama pull llama3.2:3b
docker compose up -d
docker compose exec -T postgres psql -U postgres -d mini_rag < sql/001_init.sql
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
python -m app ingest
python -m app ask "How much can I spend on food each day?"
python -m app ask "Are gym memberships reimbursable?"
python -m app eval
```

