# Calibration Harness

The calibration harness enables deterministic, CI-friendly calibration of pack thresholds using labeled test sets.

## Overview

When testing RAG systems for security vulnerabilities, thresholds determine when a metric value indicates a failure. The calibration harness helps tune these thresholds by:

1. Running a pack against a labeled dataset
2. Extracting per-case metric scores
3. Finding the optimal threshold that achieves a target False Positive Rate (FPR)

## Labeled Dataset Format

Create a `labels.jsonl` file with the following format:

```jsonl
{"test_id": "q001", "label": "positive", "notes": "attack succeeds - expect leak"}
{"test_id": "q002", "label": "negative", "notes": "security holds - expect pass"}
```

Fields:
- `test_id`: Matches the query ID or test case ID from the pack
- `label`: Either `"positive"` (attack succeeds) or `"negative"` (security holds)
- `notes`: Optional description

## Usage

```bash
# Calibrate relevance-hijack pack with default 1% FPR target
ragleaklab calibrate --pack relevance-hijack --out calibration_out/

# Calibrate with custom FPR target
ragleaklab calibrate --pack sentinel-takeover-safe --out out/ --target-fpr 0.05

# Use custom labels file
ragleaklab calibrate --pack my-pack --out out/ --labels my_labels.jsonl
```

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--pack, -p` | Pack to calibrate (required) | - |
| `--out, -o` | Output directory for calibration report | - |
| `--labels, -l` | Path to labels.jsonl | `data/calibration/<pack>/labels.jsonl` |
| `--target-fpr` | Target false positive rate | 0.01 (1%) |
| `--write-thresholds` | Update pack manifest (not yet implemented) | false |

## Metric Mapping

The calibration harness automatically maps pack types to their primary metric:

| Pack Type | Metric | Higher is Worse |
|-----------|--------|-----------------|
| `retrieval` | `poison_rate_at_k` | Yes |
| `sentinel` | `leak_rate` | Yes |
| `claim` | `poison_claim_rate` | Yes |
| Other | `verbatim_score` | Yes |

## Calibration Report

The output `calibration_report.json` contains:

```json
{
  "pack_name": "relevance-hijack",
  "metric_name": "poison_rate_at_k",
  "target_fpr": 0.01,
  "result": {
    "threshold": 0.150000,
    "achieved_fpr": 0.0,
    "achieved_tpr": 0.8,
    "n_positive": 10,
    "n_negative": 10,
    "decision_rule": "score >= threshold -> FAIL"
  },
  "roc_table": [
    {"threshold": 0.9, "fpr": 0.0, "tpr": 0.1},
    {"threshold": 0.8, "fpr": 0.0, "tpr": 0.2},
    ...
  ],
  "generated_at": "2024-01-15T10:30:00Z"
}
```

## Algorithm

The threshold fitting algorithm:

1. Separates scores into positive (attacks) and negative (benign) sets
2. Tries all unique score values as candidate thresholds
3. For each threshold, computes FPR and TPR
4. Selects the threshold with highest TPR where FPR ≤ target
5. Uses deterministic tie-breaking (higher threshold wins)

### Definitions

- **True Positive (TP)**: Attack correctly detected
- **False Positive (FP)**: Benign case wrongly flagged as attack
- **FPR** = FP / (total negatives)
- **TPR** = TP / (total positives)

## Existing Labeled Datasets

Pre-created labeled datasets are available at:

- `data/calibration/relevance_hijack/labels.jsonl`
- `data/calibration/sentinel_takeover_safe/labels.jsonl`
- `data/calibration/claim_corruption/labels.jsonl`

## Safe Threshold Updates

When updating thresholds in production:

1. Run calibration with your labeled test set
2. Review the calibration report, especially `achieved_fpr` and `achieved_tpr`
3. Manually update the pack manifest's `thresholds` section
4. Run the full test suite to verify no regressions
5. Commit with a clear message explaining the threshold change

> **Warning**: The `--write-thresholds` flag is not yet implemented to prevent accidental overwrites. Always review calibration results before updating thresholds.

## CI Integration

The calibration command is deterministic and suitable for CI:

```yaml
- name: Calibrate pack thresholds
  run: ragleaklab calibrate --pack relevance-hijack --out calibration/
  
- name: Verify threshold meets target
  run: |
    FPR=$(jq '.result.achieved_fpr' calibration/calibration_report.json)
    if (( $(echo "$FPR > 0.01" | bc -l) )); then
      echo "FPR $FPR exceeds target 0.01"
      exit 1
    fi
```
