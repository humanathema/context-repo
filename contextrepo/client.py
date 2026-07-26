"""CLI client for a running context-repo server.

Usage:
    python -m contextrepo.client write <compartment> "<content>" [--key KEY]
    python -m contextrepo.client query <compartment> "<query text>" [--k 5]
    python -m contextrepo.client compartments
    python -m contextrepo.client forget <compartment> <node_id>
"""
import argparse
import json

import requests
from rich.console import Console
from rich.table import Table

console = Console()


def _base_url(args) -> str:
    return args.url.rstrip("/")


def cmd_write(args) -> None:
    resp = requests.post(
        f"{_base_url(args)}/write",
        json={"compartment": args.compartment, "content": args.content, "key": args.key},
        timeout=30,
    )
    resp.raise_for_status()
    console.print(resp.json())


def cmd_query(args) -> None:
    resp = requests.post(
        f"{_base_url(args)}/query",
        json={"compartment": args.compartment, "query": args.query, "k": args.k},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    table = Table(title=f"query: {args.query!r}  (confidence {data['confidence']:.3f})")
    table.add_column("score")
    table.add_column("id", overflow="fold")
    table.add_column("content", overflow="fold")
    for hit in data["results"]:
        table.add_row(f"{hit['score']:.3f}", hit["id"][:8], hit["content"])
    console.print(table)


def cmd_compartments(args) -> None:
    resp = requests.get(f"{_base_url(args)}/compartments", timeout=30)
    resp.raise_for_status()
    console.print(resp.json())


def cmd_forget(args) -> None:
    resp = requests.delete(
        f"{_base_url(args)}/compartments/{args.compartment}/nodes/{args.node_id}", timeout=30
    )
    resp.raise_for_status()
    console.print(resp.json())


def main() -> None:
    parser = argparse.ArgumentParser(description="context-repo CLI client")
    parser.add_argument("--url", default="http://localhost:8420", help="context-repo server base URL")
    sub = parser.add_subparsers(required=True)

    p_write = sub.add_parser("write", help="write or merge a fact into a compartment")
    p_write.add_argument("compartment")
    p_write.add_argument("content")
    p_write.add_argument("--key", default=None)
    p_write.set_defaults(func=cmd_write)

    p_query = sub.add_parser("query", help="retrieve top-k facts from a compartment")
    p_query.add_argument("compartment")
    p_query.add_argument("query")
    p_query.add_argument("--k", type=int, default=5)
    p_query.set_defaults(func=cmd_query)

    p_compartments = sub.add_parser("compartments", help="list compartments and their sizes")
    p_compartments.set_defaults(func=cmd_compartments)

    p_forget = sub.add_parser("forget", help="delete a node by id")
    p_forget.add_argument("compartment")
    p_forget.add_argument("node_id")
    p_forget.set_defaults(func=cmd_forget)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
