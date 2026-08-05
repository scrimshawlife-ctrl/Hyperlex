"""CLI entry — uses the symbolic module structure."""
import json
from . import (
    detect_memetic_patterns,
    mock_integrate_with_external_signal,
    emit_receipt,
    PKG_VERSION,
)

def main():
    print(f"=== Hyperlex {PKG_VERSION} — Memetic Emergence Scanner (numogram+chaos) ===")
    result = detect_memetic_patterns()
    print(json.dumps(result, indent=2)[:1600] + "...\n")

    print("=== Real ingest (glossary) + full analysis ===")
    real = detect_memetic_patterns(
        query="sharp money revenge narrative hyperstition",
        ingest_source="real"
    )
    print("Virality:", real["analysis"]["virality"])
    print("Hyperstition:", real["analysis"]["hyperstition"])

    sig = mock_integrate_with_external_signal(real)
    print("\nExternal signal:", sig["actionable"], sig["confidence"])

    receipt_path = emit_receipt(real)
    print(f"\n✓ Receipt written: {receipt_path}")

    print("\n=== Reddit sample ===")
    reddit = detect_memetic_patterns(query="betting slang", ingest_source="reddit")
    print("Observed (first 180):", reddit["observed"][:180])

if __name__ == "__main__":
    main()
