"""CLI entry — demonstrates expanded ingest + schemas (v1.6)"""
import sys
import json
import argparse
from . import (
    detect_memetic_patterns,
    fetch_ingest,
    mock_integrate_with_external_signal,
    emit_receipt,
    schemas,
    PKG_VERSION,
)

def main():
    parser = argparse.ArgumentParser(description="Hyperlex Memetic Emergence Scanner")
    parser.add_argument("--query", default="agent memory context provenance", help="Query for analysis")
    parser.add_argument("--source", default="moltbook", choices=["moltbook", "urban", "combined"], help="Ingest source")
    parser.add_argument("--memory", action="store_true", help="Focus on memetic memory/efficiency")
    parser.add_argument("--export-hyperlexical", action="store_true", help="Export Moltbook batch to 007 hyperlexical dataset rows")
    args = parser.parse_args()

    print(f"=== Hyperlex {PKG_VERSION} — Memetic Emergence Scanner (numogram+chaos) ===")
    print("Schemas loaded:", bool(schemas.INGEST_SCHEMA))

    print("\n--- Analysis ---")
    result = detect_memetic_patterns(
        query=args.query,
        ingest_source=args.source,
        use_structured_ingest=False,
        validate=True
    )
    print("Virality:", result["analysis"]["virality"])
    print("Hyperstition:", result["analysis"]["hyperstition"])
    print("Schema validation:", result.get("schema_validation"))

    sig = mock_integrate_with_external_signal(result)
    print("\nExternal signal:", sig["actionable"], "confidence=", sig["confidence"])

    if args.memory or args.source == "moltbook":
        print("\n--- Memetic memory / efficiency ---")
        mm = result["analysis"]["memetic_memory"]
        eff = result.get("memetic_efficiency", result["analysis"].get("memetic_efficiency", {}))
        print("Memory tiers:", mm["memory_tiers"])
        print("Efficiency:", eff.get("efficiency_score") if isinstance(eff, dict) else eff)
        print("Provenance required:", mm["provenance_required"])
        print("Virality (with eff):", result["analysis"]["virality"])

    receipt_path = emit_receipt(result, validate=True)
    print(f"\n✓ Receipt written with validation: {receipt_path}")

    print("\n--- Schema access ---")
    print("Ingest schema keys:", list(schemas.get_ingest_schema().keys())[:3])

    if args.export_hyperlexical:
        print("\n--- Exporting to 007 hyperlexical format ---")
        try:
            import subprocess
            from pathlib import Path
            batch = Path("out/batch_moltbook_memetics.json")
            if batch.exists():
                subprocess.run([sys.executable, "scripts/moltbook_to_hyperlexical.py", "--batch", str(batch), "--out", "data/moltbook_hyperlexical_rows.jsonl"], check=False, timeout=30)
                print("Exported Moltbook → hyperlexical rows (ai-native + memory typology)")
            else:
                print("No batch found for export. Run with --memory --source moltbook first.")
        except Exception as e:
            print(f"Export error: {e}")

if __name__ == "__main__":
    main()
