from __future__ import annotations

import argparse

from app.search.index import CorpusSearchEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a minimal retrieval demo over processed documents")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of hits to return")
    args = parser.parse_args()

    engine = CorpusSearchEngine()
    hits = engine.search(args.query, top_k=args.top_k)
    if not hits:
        print("No hits found. Process documents first with scripts.batch_process or the API.")
        return

    print(f"Query: {args.query}")
    print()
    for idx, hit in enumerate(hits, start=1):
        print(f"{idx}. file={hit.filename} score={hit.score}")
        print(hit.snippet)
        print()


if __name__ == "__main__":
    main()

