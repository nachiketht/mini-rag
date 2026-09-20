import argparse

from app.ingest import run as ingest_run
from app.pgadapter import PgAdapter


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="Chunk, embed, and upsert the expense policy")

    args = parser.parse_args(argv)

    if args.command == "ingest":
        count = ingest_run(PgAdapter())
        print(f"Ingested {count} chunks")
