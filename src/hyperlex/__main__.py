"""CLI entry — demonstrates expanded ingest + schemas (v1.6)"""
import json
from . import (
    detect_memetic_patterns,
    fetch_ingest,
    mock_integrate_with_external_signal,
    emit_receipt,
    schemas,
    PKG_VERSION,
)

def main():
    print(f"=== Hyperlex {PKG_VERSION} — Memetic Emergence Scanner (numogram+chaos) ===")
    print("Schemas loaded:", bool(schemas.INGEST_SCHEMA))

    print("\n--- Structured Ingest Demo ---")
    structured = fetch_ingest("sharp money hyperstition", source="combined", structured=True)
    print(json.dumps(structured, indent=2)[:600] + "...\n")

    print("--- Full analysis with structured ingest + validation ---")
    result = detect_memetic_patterns(
        query="revenge narrative sharp action",
        ingest_source="urban",
        use_structured_ingest=True,
        validate=True
    )
    print("Virality:", result["analysis"]["virality"])
    print("Hyperstition:", result["analysis"]["hyperstition"])
    print("Schema validation:", result.get("schema_validation"))

    sig = mock_integrate_with_external_signal(result)
    print("\nExternal signal:", sig["actionable"], "confidence=", sig["confidence"])

    # Demo Moltbook agent memetics (new)
    print("\n--- Moltbook agent memory memetics demo ---")
    mem_res = detect_memetic_patterns(
        "KDR context loss episodic rubric ghost in the cache provenance ECHO",
        ingest_source="moltbook"
    )
    mm = mem_res["analysis"]["memetic_memory"]
    eff = mem_res["analysis"].get("memetic_efficiency", {})
    print("Memory tiers:", mm["memory_tiers"])
    print("Efficiency:", eff.get("efficiency_score"))
    print("Provenance required:", mm["provenance_required"])
    print("Synthesis with efficiency:", mock_integrate_with_external_signal(mem_res)["memetic_efficiency"])

    receipt_path = emit_receipt(result, validate=True)
    print(f"\n✓ Receipt written with validation: {receipt_path}")

    print("\n--- Schema access ---")
    print("Ingest schema keys:", list(schemas.get_ingest_schema().keys())[:3])

if __name__ == "__main__":
    main()
