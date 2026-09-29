"""Per-family errors keep OBSERVED and INFERRED apart."""

from hyperlexical.classify_error_audit import confusion_matrix, error_report
from hyperlexical.classify_metrics import macro_f1_nonnone


def _row(gold: str, pred: str, evidence: str) -> dict[str, str]:
    return {"evidence": evidence, "gold": gold, "pred": pred}


def test_observed_and_inferred_are_separate_and_none_stays_out_of_macro():
    rows = [
        _row("ai-native", "ai-native", "OBSERVED"),
        _row("ai-native", "none", "OBSERVED"),
        _row("gaming-meta", "none", "OBSERVED"),
        _row("ai-native", "crypto-degen", "INFERRED"),
        _row("none", "none", "INFERRED"),
    ]
    report = error_report(rows)
    assert report["observed"]["n"] == 3
    assert report["inferred"]["n"] == 2
    assert report["observed"]["accuracy"] == 1 / 3
    assert report["inferred"]["accuracy"] == 0.5
    observed_gold = ["ai-native", "ai-native", "gaming-meta"]
    observed_pred = ["ai-native", "none", "none"]
    assert report["observed"]["classify_macro_f1_nonnone"] == macro_f1_nonnone(observed_gold, observed_pred)
    assert report["observed"]["none_prediction_rate_on_non_none"] == 2 / 3
    assert report["observed"]["error_clusters"][0]["pred"] == "none"
    assert report["observed"]["families"]["ai-native"]["n"] == 2
    assert "ai-native" in confusion_matrix(observed_gold, observed_pred)


def test_perfect_observed_family_has_full_recall():
    rows = [_row("betting-sharp", "betting-sharp", "OBSERVED") for _ in range(4)]
    report = error_report(rows)
    family = report["observed"]["families"]["betting-sharp"]
    assert family["precision"] == 1
    assert family["recall"] == 1
    assert family["f1"] == 1
    assert family["n"] == 4
    assert report["inferred"] is None
    assert report["observed"]["error_clusters"] == []
