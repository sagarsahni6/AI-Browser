"""
tests/e2e/run_all_e2e.py — Standalone CLI Runner for AI Browser 2.0 E2E Test Suite.

Supports:
  --tier {1, 2, 3, 4, all} : Select target test tier
  -v, --verbose            : Verbose test output
  -k, --filter EXPRESSION  : Pytest keyword filter expression
  -x, --exitfirst          : Exit immediately on first failure

Usage:
  python tests/e2e/run_all_e2e.py --tier 1 -v
"""

import sys
import os
import argparse
from pathlib import Path
import pytest

# Ensure workspace root is at head of sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Enforce hermetic test environment variables
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["TESTING"] = "1"


def main():
    parser = argparse.ArgumentParser(description="AI Browser 2.0 E2E Test Suite Runner")
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Target test tier: 1=Feature Coverage, 2=Boundary Analysis, 3=Pairwise, 4=Scenarios, all=Full Suite"
    )
    parser.add_argument("-v", "--verbose", action="store_true", default=True, help="Verbose pytest output")
    parser.add_argument("-k", "--filter", type=str, default="", help="Pytest keyword expression filter")
    parser.add_argument("-x", "--exitfirst", action="store_true", default=False, help="Stop on first failure")
    parser.add_argument("-q", "--quiet", action="store_true", default=False, help="Minimal quiet output")
    args, extra_args = parser.parse_known_args()

    pytest_args = [
        "-o", "asyncio_mode=auto",
        "-o", "asyncio_default_fixture_loop_scope=function",
        "-W", "ignore::DeprecationWarning",
    ]

    if args.quiet:
        pytest_args.append("-q")
    elif args.verbose:
        pytest_args.append("-v")

    if args.exitfirst:
        pytest_args.append("-x")

    if args.filter:
        pytest_args.extend(["-k", args.filter])

    e2e_dir = Path(__file__).resolve().parent
    if args.tier == "1":
        pytest_args.append(str(e2e_dir / "tier1_features"))
    elif args.tier == "2":
        pytest_args.append(str(e2e_dir / "tier2_boundaries"))
    elif args.tier == "3":
        pytest_args.append(str(e2e_dir / "tier3_cross_feature"))
    elif args.tier == "4":
        pytest_args.append(str(e2e_dir / "tier4_scenarios"))
    else:
        pytest_args.append(str(e2e_dir))

    pytest_args.extend(extra_args)

    print("=" * 80)
    print(f" AI BROWSER 2.0 — END-TO-END (E2E) TEST SUITE RUNNER")
    print(f" Tier Selection : {args.tier.upper()} | Python: {sys.version.split()[0]}")
    print(f" Directory      : {e2e_dir}")
    print("=" * 80)

    exit_code = pytest.main(pytest_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(f" [PASS] 100% of executed Tier {args.tier.upper()} E2E tests PASSED successfully.")
    else:
        print(f" [FAIL] E2E test run finished with exit code {exit_code}.")
    print("=" * 80)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
