"""Command-line entry point for the local-first demonstrator."""
from __future__ import annotations

import argparse
import json
import sys

from .demo import WorkstationDemoError, run_local_demo
from .verify import CaseVerificationError, verify_case


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="elite-workstation")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="run the local Ingestion Core → Protocol case demonstrator")
    demo.add_argument("input", help="local JSONL or CSV source file")
    demo.add_argument("--case-dir", required=True, help="new case directory; existing directories are never overwritten")
    demo.add_argument("--source-id", required=True)
    demo.add_argument("--source-uri", required=True)
    demo.add_argument("--observed-at", required=True, help="explicit source observation timestamp (RFC 3339)")
    demo.add_argument("--collected-at", required=True, help="explicit collection timestamp (RFC 3339)")
    demo.add_argument("--ingestion-core", required=True, help="trusted local ELITE-Ingestion-Core checkout")
    demo.add_argument("--protocol", required=True, help="trusted local ELITE-Protocol checkout")
    demo.add_argument("--format", choices=("jsonl", "csv"))
    demo.add_argument(
        "--operator-asserts-authorized", action="store_true",
        help="operator assertion only; does not authenticate or enforce legal/policy authorization",
    )
    verify = sub.add_parser("verify", help="verify a completed local case")
    verify.add_argument("case_dir", help="case directory to verify")
    verify.add_argument("--protocol", help="trusted local ELITE-Protocol checkout for schema validation")

    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            result = verify_case(args.case_dir, protocol_path=args.protocol)
        else:
            result = run_local_demo(
            input_path=args.input,
            case_path=args.case_dir,
            source_id=args.source_id,
            source_uri=args.source_uri,
            observed_at=args.observed_at,
            collected_at=args.collected_at,
            ingestion_core_path=args.ingestion_core,
            protocol_path=args.protocol,
            source_format=args.format,
                operator_asserts_authorized=args.operator_asserts_authorized,
            )
    except (OSError, ValueError, WorkstationDemoError, CaseVerificationError) as exc:
        parser.exit(2, f"elite-workstation: {exc}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
