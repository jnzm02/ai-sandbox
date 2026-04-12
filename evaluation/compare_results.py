"""
Compare two evaluation results to see if a change improved metrics.

Usage:
    python evaluation/compare_results.py baseline_OLD.json baseline_NEW.json
"""

import json
import sys
from pathlib import Path


def load_result(filepath):
    """Load result JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def compare_metrics(old, new):
    """Compare metrics between two results"""

    print("\n" + "=" * 70)
    print("📊 EXPERIMENT COMPARISON")
    print("=" * 70)

    # Extract metrics
    old_recall = old['quality_metrics']['recall_at_3']['mean']
    new_recall = new['quality_metrics']['recall_at_3']['mean']

    old_faith = old['quality_metrics']['faithfulness']['mean']
    new_faith = new['quality_metrics']['faithfulness']['mean']

    old_relev = old['quality_metrics']['relevance']['mean']
    new_relev = new['quality_metrics']['relevance']['mean']

    old_p50 = old['performance']['latency']['p50_ms']
    new_p50 = new['performance']['latency']['p50_ms']

    old_p95 = old['performance']['latency']['p95_ms']
    new_p95 = new['performance']['latency']['p95_ms']

    old_cost = old['performance']['cost']['cost_per_100_queries_usd']
    new_cost = new['performance']['cost']['cost_per_100_queries_usd']

    # Calculate deltas
    recall_delta = new_recall - old_recall
    faith_delta = new_faith - old_faith
    relev_delta = new_relev - old_relev
    p50_delta = new_p50 - old_p50
    p95_delta = new_p95 - old_p95
    cost_delta = new_cost - old_cost

    # Print comparison
    print("\n🎯 Quality Metrics:")
    print(f"   Recall@3:      {old_recall:.3f} → {new_recall:.3f}  " + format_delta(recall_delta, higher_is_better=True))
    print(f"   Faithfulness:  {old_faith:.3f} → {new_faith:.3f}  " + format_delta(faith_delta, higher_is_better=True))
    print(f"   Relevance:     {old_relev:.3f} → {new_relev:.3f}  " + format_delta(relev_delta, higher_is_better=True))

    print("\n⏱️  Performance:")
    print(f"   p50 Latency:   {old_p50:.0f}ms → {new_p50:.0f}ms  " + format_delta(p50_delta, higher_is_better=False, unit="ms"))
    print(f"   p95 Latency:   {old_p95:.0f}ms → {new_p95:.0f}ms  " + format_delta(p95_delta, higher_is_better=False, unit="ms"))

    print("\n💰 Cost:")
    print(f"   Per 100:       ${old_cost:.4f} → ${new_cost:.4f}  " + format_delta(cost_delta, higher_is_better=False, unit="$"))

    # Decision recommendation
    print("\n" + "=" * 70)
    print("🧠 DECISION RECOMMENDATION")
    print("=" * 70)

    keep_change = True
    reasons = []

    # Quality checks
    if recall_delta < -0.05:  # >5% drop in recall
        keep_change = False
        reasons.append("❌ Recall dropped significantly")
    elif recall_delta > 0.05:
        reasons.append("✅ Recall improved significantly")

    if faith_delta < -0.05:  # >5% drop in faithfulness
        keep_change = False
        reasons.append("❌ Faithfulness dropped significantly")
    elif faith_delta > 0.05:
        reasons.append("✅ Faithfulness improved significantly")

    # Performance checks
    if p95_delta > 500:  # >500ms increase in p95
        keep_change = False
        reasons.append("❌ p95 latency increased significantly")
    elif p95_delta < -500:
        reasons.append("✅ p95 latency improved significantly")

    # Cost checks
    if cost_delta > old_cost * 0.5:  # >50% cost increase
        keep_change = False
        reasons.append("❌ Cost increased significantly")

    # Print decision
    if keep_change:
        print("\n✅ RECOMMENDATION: KEEP THE CHANGE")
    else:
        print("\n❌ RECOMMENDATION: REVERT THE CHANGE")

    if reasons:
        print("\nReasons:")
        for reason in reasons:
            print(f"  {reason}")
    else:
        print("\n⚠️  No significant changes detected. Consider if effort was worth it.")

    print("\n" + "=" * 70)


def format_delta(delta, higher_is_better=True, unit=""):
    """Format delta with color and direction indicator"""

    if abs(delta) < 0.001 and unit != "ms" and unit != "$":  # Ignore tiny changes
        return "→ (no change)"

    if unit == "ms" or unit == "$":
        abs_delta = abs(delta)
        if unit == "ms":
            delta_str = f"{abs_delta:+.0f}{unit}"
        else:
            delta_str = f"{unit}{abs_delta:+.4f}"
    else:
        delta_str = f"{delta:+.3f} ({delta*100:+.1f}%)"

    # Determine if good or bad
    if higher_is_better:
        is_good = delta > 0
    else:
        is_good = delta < 0

    if is_good:
        return f"✅ {delta_str}"
    else:
        return f"❌ {delta_str}"


def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_results.py <old_result.json> <new_result.json>")
        print("\nExample:")
        print("  python evaluation/compare_results.py \\")
        print("    evaluation/results/baseline_20260413_014642.json \\")
        print("    evaluation/results/baseline_20260413_023045.json")
        sys.exit(1)

    old_path = sys.argv[1]
    new_path = sys.argv[2]

    # Check files exist
    if not Path(old_path).exists():
        print(f"Error: {old_path} not found")
        sys.exit(1)

    if not Path(new_path).exists():
        print(f"Error: {new_path} not found")
        sys.exit(1)

    # Load results
    old = load_result(old_path)
    new = load_result(new_path)

    # Compare
    compare_metrics(old, new)


if __name__ == "__main__":
    main()