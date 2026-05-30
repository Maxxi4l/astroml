from __future__ import annotations

import argparse
import json
import os
import pathlib
from typing import Optional

from .db.session import load_database_config
from .ingestion.service import IngestionService
from .ingestion.state import StateStore


CLI_DESCRIPTION = """\
AstroML utilities CLI — manage ingestion, configuration, and the
quick-start pipeline from a single entrypoint.

For full usage, see the README "Usage" section:
  https://github.com/Traqora/astroml#usage
"""

CLI_EPILOG = """\
Examples:
  # Run incremental ingestion for a ledger range
  python -m astroml.cli ingest --start 1000 --end 1100

  # Print the effective database configuration that AstroML will use
  python -m astroml.cli config --print-db

  # Same, but read the YAML config from a custom path
  python -m astroml.cli --config ./custom/database.yaml config --print-db

  # Run the end-to-end quick start with sample data
  python -m astroml.cli quickstart --num-ledgers 200 --epochs 5

  # Preprocess a backfill dataset into Parquet
  python -m astroml.cli preprocess-backfill --input data.csv --output out.parquet

  # Select a runtime environment (sets ASTROML_ENV for downstream loaders)
  python -m astroml.cli --env production config --print-db

Environment variables:
  ASTROML_DATABASE_URL  Overrides the database URL from config/database.yaml.
  ASTROML_ENV           Runtime environment name (development | production).
                        Set automatically by --env when provided.
"""


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="astroml",
        description=CLI_DESCRIPTION,
        epilog=CLI_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=None,
        metavar="PATH",
        help=(
            "Path to the database YAML config (default: config/database.yaml). "
            "Used by `config --print-db` and any subcommand that reads the "
            "database configuration."
        ),
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        metavar="NAME",
        help=(
            "Runtime environment name (e.g. development, production). "
            "When provided, sets ASTROML_ENV for downstream loaders unless "
            "ASTROML_ENV is already set in the process environment."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Incremental ingestion of ledgers")
    ingest.add_argument("--start", type=int, default=None, help="Start ledger id (inclusive)")
    ingest.add_argument("--end", type=int, default=None, help="End ledger id (inclusive)")
    ingest.add_argument(
        "--state-file",
        type=str,
        default=None,
        help="Path to state file (defaults to ./.astroml_state/ingestion_state.json)",
    )

    config = sub.add_parser("config", help="Configuration management")
    config.add_argument(
        "--print-db",
        action="store_true",
        help="Print effective database configuration",
    )

    quickstart = sub.add_parser(
        "quickstart",
        help="Run quick start: ingestion → graph → train pipeline with sample data",
    )
    quickstart.add_argument(
        "--num-ledgers",
        type=int,
        default=100,
        help="Number of sample ledgers to generate (default: 100)",
    )
    quickstart.add_argument(
        "--num-accounts",
        type=int,
        default=50,
        help="Number of sample accounts (default: 50)",
    )
    quickstart.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Training epochs (default: 10)",
    )
    quickstart.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    preprocess = sub.add_parser(
        "preprocess-backfill",
        help="Preprocess large ledger backfill datasets using Polars",
    )
    preprocess.add_argument(
        "--input",
        required=True,
        help="Input file or directory (csv, parquet, ndjson/jsonl).",
    )
    preprocess.add_argument(
        "--output",
        required=True,
        help="Output Parquet path.",
    )
    preprocess.add_argument(
        "--input-format",
        choices=["parquet", "csv", "ndjson", "jsonl"],
        default=None,
        help="Optional explicit input format.",
    )

    args = parser.parse_args(argv)

    # Wire the top-level --env flag into ASTROML_ENV so downstream loaders
    # (see docs/api/configuration.md) see the requested environment.
    # Do not overwrite an env var the operator already set explicitly.
    if args.env and "ASTROML_ENV" not in os.environ:
        os.environ["ASTROML_ENV"] = args.env

    if args.command == "ingest":
        store = StateStore(path=args.state_file) if args.state_file else StateStore()
        service = IngestionService(state_store=store)

        # Example fetch/process functions; in real usage, users would customize/import
        def fetch_fn(ledger_id: int):
            # Placeholder fetch, replace with real data retrieval
            return {"ledger": ledger_id, "data": f"payload-{ledger_id}"}

        def process_fn(ledger_id: int, payload: dict):
            # Placeholder processing; replace with DB writes or other side effects
            # For CLI visibility we do minimal printing; real apps would use logging
            print(f"processed ledger {ledger_id}")

        result = service.ingest(
            start_ledger=args.start,
            end_ledger=args.end,
            fetch_fn=fetch_fn,
            process_fn=process_fn,
        )
        print(json.dumps({
            "attempted": result.attempted,
            "processed": result.processed,
            "skipped": result.skipped,
        }, indent=2))
        return 0

    if args.command == "config":
        if args.print_db:
            try:
                db_config = load_database_config(args.config)
                print("Effective database configuration:")
                print(json.dumps({
                    "host": db_config.host,
                    "port": db_config.port,
                    "name": db_config.name,
                    "user": db_config.user,
                    "password": "***" if db_config.password else "",
                    "url": db_config.to_url()
                }, indent=2))
                return 0
            except FileNotFoundError as e:
                print(f"Error: {e}")
                return 1
            except Exception as e:
                print(f"Error loading config: {e}")
                return 1
        else:
            config.print_help()
            return 1

    if args.command == "quickstart":
        from .quick_start import run_quickstart, QuickStartConfig
        
        # Update config with CLI arguments
        QuickStartConfig.NUM_SAMPLE_LEDGERS = args.num_ledgers
        QuickStartConfig.NUM_ACCOUNTS = args.num_accounts
        QuickStartConfig.TRAIN_EPOCHS = args.epochs
        QuickStartConfig.RANDOM_SEED = args.seed
        
        return run_quickstart()

    if args.command == "preprocess-backfill":
        from .preprocessing.ledger_backfill import preprocess_to_parquet

        output_path = preprocess_to_parquet(
            input_path=args.input,
            output_path=args.output,
            input_format=args.input_format,
        )
        print(json.dumps({"output": str(output_path)}, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
