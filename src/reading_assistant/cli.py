import argparse
import json
from pathlib import Path

from .engine import Recommender, load_catalog


def main():
    parser = argparse.ArgumentParser(
        description="Source-grounded reading recommendations"
    )
    parser.add_argument(
        "--catalog", help="Validated source catalog JSON; defaults to synthetic demo"
    )
    parser.add_argument(
        "--audience",
        action="append",
        help="Trusted local audience; repeat for multiple groups",
    )
    parser.add_argument(
        "--model", help="Optional installed local Ollama model; no downloads"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    recommend = commands.add_parser("recommend")
    recommend.add_argument("draft", type=Path)
    recommend.add_argument("--output", type=Path)
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=4174)
    args = parser.parse_args()
    if args.command == "serve":
        from .server import create_app

        create_app(args.catalog, args.audience or ["demo"], args.model).run(
            host="127.0.0.1", port=args.port, threaded=True
        )
    else:
        try:
            result = Recommender(
                load_catalog(args.catalog), args.audience or ["demo"], args.model
            ).recommend(args.draft.read_text())
        except (ValueError, OSError) as error:
            parser.error(str(error))
        output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(output)
        else:
            print(output, end="")


if __name__ == "__main__":
    main()
