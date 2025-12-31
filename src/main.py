from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Log Report Automation - generate simple reports from CSV logs."
    )
    parser.add_argument(
        "--input",
        default="sample_data/example.csv",
        help="Path to input CSV file (default: sample_data/example.csv)",
    )
    parser.add_argument(
        "--output",
        default="report.xlsx",
        help="Path to output Excel report (default: report.xlsx)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    print("✅ Log Report Automation")
    print(f"Input : {input_path.resolve()}")
    print(f"Output: {output_path.resolve()}")
    print("Next step: implement CSV parsing + Excel report generation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())