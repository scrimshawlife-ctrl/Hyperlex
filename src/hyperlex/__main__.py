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

    receipt_path = emit_receipt(result, validate=True)
    print(f"\n✓ Receipt written with validation: {receipt_path}")

    print("\n--- Schema access ---")
    print("Ingest schema keys:", list(schemas.get_ingest_schema().keys())[:3])

if __name__ == "__main__":
    main()
