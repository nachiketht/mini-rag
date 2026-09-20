import argparse
import json

from app.eval import run as eval_run
from app.generate import generate
from app.ingest import run as ingest_run
from app.pgadapter import PgAdapter
from app.retrieve import search


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="Chunk, embed, and upsert the expense policy")
    ask = sub.add_parser("ask", help="Answer a question from the policy with a citation")
    ask.add_argument("question")
    sub.add_parser("eval", help="Ask the six required questions and write tests/output.json")

    args = parser.parse_args(argv)
    adapter = PgAdapter()

    if args.command == "ingest":
        count = ingest_run(adapter)
        print(f"Ingested {count} chunks")
        return

    if args.command == "ask":
        hits = search(args.question, adapter)
        result = generate(args.question, hits)
        print(json.dumps(result, indent=2))
        return

    if args.command == "eval":
        results = eval_run(adapter)
        print(json.dumps(results, indent=2))
