# Technical Report: reco_ssl_test_20260305_160644

## Scope
- Target host: `https://194.58.95.112` (SSL, `curl --insecure`)
- Auth flow:
  - `POST /api/auth/login` with `{"username":"doctor","password":"***"}`
  - JWT token from `access_token`
- Test endpoint:
  - `POST /api/recommendations/interpret`
  - Header: `Authorization: Bearer <token>`
  - Body: `{"text":"..."}`  

## Result Summary
- Total cases: `13`
- Passed: `13`
- Failed: `0`
- Pass rate: `100.00%`
- Warnings (autocorrect/domain): `6` total in `4` cases
- Confidence:
  - min: `0.8405`
  - avg: `0.9419`
  - max: `1.0000`
- Low confidence cases (`<0.70`): `0`

## Parser Behavior
- `parse_method` distribution:
  - `hybrid`: `12`
  - `rule_regex`: `1`
- `ml_classifier` fallback: not used in this run (all cases resolved via rules/fuzzy cascade).

## Coverage by Recommendation Type
- `basal_rate`: 2
- `carb_ratio`: 1
- `correction_factor`: 1
- `target_range`: 1
- `target_glucose`: 1
- `prebolus_time`: 1
- `temp_basal_percent`: 1
- `active_insulin_time`: 1
- `correction_interval`: 1
- `low_glucose_alert_threshold`: 1
- `high_glucose_alert_threshold`: 1
- `dual_bolus_split`: 1

## Warnings Breakdown
- Case 3:
  - `autocorrect:коэф->коэффициент`
  - `autocorrect:угл->углеводный`
- Case 4:
  - `autocorrect:чуствит->чувствит`
  - `autocorrect:ммольл->ммоль/л`
- Case 8:
  - `autocorrect:врем ->временная `
- Case 10:
  - `autocorrect:корригировать->корректировать`

These warnings are expected normalization events, not parse failures.

## Output Contract (per case)
For each response, report includes:
- Type classification: `recommendation_type`
- Numeric payload: `value`, `value_min`, `value_max`
- Units and temporal bounds: `unit`, `time_start`, `time_end`
- Context metadata: `condition`
- Explainability: `confidence`, `parse_method`, `trace`
- Data quality notes: `errors_or_warnings`

## Artifacts
- Raw JSONL: `reports/reco_ssl_test_20260305_160644.jsonl`
- Pretty JSON: `reports/reco_ssl_test_20260305_160644_pretty.json`
- Markdown Table: `reports/reco_ssl_test_20260305_160644_table.md`
- Raw Summary JSON: `reports/reco_ssl_test_20260305_160644_summary.json`

