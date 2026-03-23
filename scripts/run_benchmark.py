from __future__ import annotations

import argparse
import json

from ehr_fhir_genomics_toolkit.benchmarking import run_benchmark


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["demo", "mock"], default="demo")
    p.add_argument("--config", default="config.mock.yaml")
    p.add_argument("--n-samples", type=int, default=500)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--no-variants", action="store_true")
    p.add_argument("--no-signatures", action="store_true")
    p.add_argument("--out-dir", default="benchmark_results")

    p.add_argument("--signature-profile", default="generic_oncology")
    p.add_argument("--signature-config", default="")
    p.add_argument("--regimen-profile", default="generic_oncology")
    p.add_argument("--regimen-config", default="")

    return p.parse_args()


def main():
    args = parse_args()
    summary = run_benchmark(
        mode=args.mode,
        n_samples=args.n_samples,
        repeats=args.repeats,
        include_variants=not args.no_variants,
        compute_signatures_flag=not args.no_signatures,
        out_dir=args.out_dir,
        config_path=args.config,
        signature_profile=args.signature_profile,
        signature_config=args.signature_config or None,
        regimen_profile=args.regimen_profile,
        regimen_config=args.regimen_config or None,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()