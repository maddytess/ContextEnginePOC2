import argparse
import asyncio
import sys

from .loader import load_package
from .validator import validate_package
from .registrar import register_package
from context_engine.setup_schema import setup_schema


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m adk",
        description="Escher ADK — register agent packages into the Context Engine",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    reg = sub.add_parser("register", help="Register an agent package")
    reg.add_argument("package_dir", help="Path to the package directory containing agent.yaml")
    reg.add_argument("--tenant-id", default=None, help="Tenant ID (omit for global registration)")
    reg.add_argument("--dry-run", action="store_true", help="Validate only, do not write to CE")
    return parser


async def _run(args: argparse.Namespace) -> int:
    print(f"Loading package: {args.package_dir}")
    try:
        pkg = load_package(args.package_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    print(f"  agent_id         : {pkg.manifest.agent_id}")
    print(f"  skills           : {[s.skill_id for s in pkg.skills]}")
    print(f"  tools            : {[t.tool_id for t in pkg.tools]}")
    print(f"  context_builders : {[cb.context_builder_id for cb in pkg.context_builders]}")

    print("\nValidating...")
    result = validate_package(pkg)

    if result.warnings:
        for w in result.warnings:
            print(f"  WARN : {w}")

    if not result.ok():
        for e in result.errors:
            print(f"  ERROR: {e}")
        print(f"\nValidation FAILED — {len(result.errors)} error(s). Nothing registered.")
        return 1

    print("  Validation passed.")

    if args.dry_run:
        print("\n--dry-run: skipping CE registration.")
        print(f"Would register: agent={pkg.manifest.agent_id!r}  skills={[s.skill_id for s in pkg.skills]}  tools={[t.tool_id for t in pkg.tools]}  context_builders={[cb.context_builder_id for cb in pkg.context_builders]}")
        return 0

    print("\nSetting up schema...")
    await setup_schema()

    print("\nRegistering package...")
    try:
        reg_result = await register_package(pkg, tenant_id=args.tenant_id)
    except Exception as e:
        print(f"ERROR during registration: {e}")
        return 1

    for tid in reg_result.tool_ids:
        print(f"  tool registered              : {tid}")
    for cb_id in reg_result.context_builder_ids:
        print(f"  context_builder registered   : {cb_id}")
    for sid in reg_result.skill_ids:
        print(f"  skill registered             : {sid}")
    print(f"  agent registered             : {reg_result.agent_id}")
    print("\nDone.")
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
