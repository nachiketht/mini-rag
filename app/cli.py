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
    sub.add_parser("ingest")
    ask = sub.add_parser("ask")
    ask.add_argument("question")
    sub.add_parser("eval")

    args = parser.parse_args(argv)
    adapter = PgAdapter()

    if args.command == "ingest":
        print(f"Ingested {ingest_run(adapter)} chunks")
        return
    if args.command == "ask":
        print(json.dumps(generate(args.question, search(args.question, adapter)), indent=2))
        return
    print(json.dumps(eval_run(adapter), indent=2))
