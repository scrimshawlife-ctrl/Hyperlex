"""Example: Running hyperlex on agent memory discourse (Moltbook style)."""

from hyperlex import detect_memetic_patterns

# Simulate or use real Moltbook data
query = "context loss KDR provenance ECHO tiered memory sliding windows"

result = detect_memetic_patterns(
    query=query,
    ingest_source="moltbook",  # uses the stub or real
    use_structured_ingest=False
)

print("=== Hyperlex on Agent Memory Memetics ===")
print("Observed:", result["observed"][:150])
print()
print("Memetic Memory Analysis:")
mm = result["analysis"]["memetic_memory"]
print(f"  Tiers: {mm['memory_tiers']}")
print(f"  Provenance required: {mm['provenance_required']}")
print(f"  Context loss technique: {mm['context_loss_technique']}")
print(f"  Compression: {mm['compression_observed']}")
print(f"  Friction: {mm['friction']}")

print()
print("Compression classification:")
print(result["analysis"]["compression"])

print()
print("Context friction:")
print(result["analysis"]["context_friction"])
