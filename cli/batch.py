"""Batch Runner CLI tool (Integration Standard Point 10)."""

import os
import sys
import json
import uuid
import time
import argparse
from pathlib import Path
import httpx


def run_batch(input_path: str, api_url: str, out_dir: str):
    in_path = Path(input_path)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    input_files = [in_path] if in_path.is_file() else list(in_path.glob("*.json"))
    print(f"[*] IncuBrix Batch Runner: Found {len(input_files)} test input files.")

    summary_records = []
    total_start = time.time()

    with httpx.Client(base_url=api_url, timeout=30.0) as client:
        for idx, file_path in enumerate(input_files, start=1):
            print(f"[{idx}/{len(input_files)}] Running input: {file_path.name}")
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            connector_key = payload.get("connector_key", "discourse")
            method = payload.get("method", "publish")
            req_body = payload.get("body", payload)

            idempotency_key = req_body.get("idempotency_key") or f"batch_{uuid.uuid4()}"
            headers = {
                "Idempotency-Key": idempotency_key,
                "Content-Type": "application/json",
            }

            url = f"/connector/v1/{connector_key}/{method}"
            start_t = time.time()
            try:
                resp = client.post(url, headers=headers, json=req_body)
                elapsed = time.time() - start_t
                result_data = resp.json()

                output_record = {
                    "input_file": file_path.name,
                    "status_code": resp.status_code,
                    "elapsed_s": round(elapsed, 3),
                    "response": result_data,
                    "idempotency_key": idempotency_key,
                }
                summary_records.append(output_record)

                # Write individual result and output manifest
                res_file = out_path / f"result_{file_path.stem}.json"
                with open(res_file, "w", encoding="utf-8") as rf:
                    json.dump(output_record, rf, indent=2)

            except Exception as e:
                err_record = {
                    "input_file": file_path.name,
                    "status_code": 500,
                    "error": str(e),
                }
                summary_records.append(err_record)

    total_elapsed = time.time() - total_start
    summary_report = {
        "timestamp": time.time(),
        "total_inputs": len(input_files),
        "total_elapsed_seconds": round(total_elapsed, 2),
        "summary": summary_records,
    }
    with open(out_path / "batch_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print(f"[+] Batch runner completed in {round(total_elapsed, 2)}s. Results written to {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="IncuBrix Batch Runner CLI")
    parser.add_argument("--input", required=True, help="Input directory or JSON file")
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    run_batch(args.input, args.api, args.out)


if __name__ == "__main__":
    main()
