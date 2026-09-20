# Mini-RAG Project on Policy with 6 Sections

## Setup

```bash
ollama serve
```

In another terminal:

```bash
ollama pull qwen3:8b
bash scripts/ensure-postgres.sh
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

