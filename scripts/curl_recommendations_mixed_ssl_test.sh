#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://194.58.95.112}"
LOGIN_PATH="${LOGIN_PATH:-/api/auth/login}"
INTERPRET_MULTI_PATH="${INTERPRET_MULTI_PATH:-/api/recommendations/interpret-multi}"
USERNAME="${USERNAME:-doctor}"
PASSWORD="${PASSWORD:-supersecretpassword123}"
INSECURE_TLS="${INSECURE_TLS:-1}"
DATASET_FILE="${DATASET_FILE:-tests/data/mixed_recommendations_ru.txt}"
REPORT_DIR="${REPORT_DIR:-reports}"
REPORT_PREFIX="${REPORT_PREFIX:-reco_mixed_ssl_test_$(date +%Y%m%d_%H%M%S)}"
REPORT_JSONL="${REPORT_DIR}/${REPORT_PREFIX}.jsonl"
REPORT_SUMMARY_JSON="${REPORT_DIR}/${REPORT_PREFIX}_summary.json"

if [[ "${INSECURE_TLS}" == "1" ]]; then
  CURL_TLS_FLAG="--insecure"
else
  CURL_TLS_FLAG=""
fi

mkdir -p "${REPORT_DIR}"
: > "${REPORT_JSONL}"

echo "[1/3] Login"
LOGIN_RESP="$(
  curl -sS ${CURL_TLS_FLAG} -X POST "${BASE_URL}${LOGIN_PATH}" \
    -H "Content-Type: application/json" \
    --data "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
TOKEN="$(printf '%s' "${LOGIN_RESP}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null || true)"
if [[ -z "${TOKEN}" ]]; then
  echo "ERROR: cannot parse access_token"
  echo "${LOGIN_RESP}"
  exit 1
fi

echo "[2/3] Mixed multi-entity tests (${DATASET_FILE})"
if [[ ! -f "${DATASET_FILE}" ]]; then
  echo "ERROR: dataset file not found: ${DATASET_FILE}"
  exit 1
fi

pass_count=0
fail_count=0
idx=0
total=0

while IFS= read -r text; do
  [[ -z "${text}" ]] && continue
  total=$((total + 1))
  idx=$((idx + 1))

  response="$(
    curl -sS ${CURL_TLS_FLAG} -X POST "${BASE_URL}${INTERPRET_MULTI_PATH}" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}, ensure_ascii=False))' "${text}")"
  )"

  eval_json="$(
    python3 -c '
import json,sys
resp = json.loads(sys.argv[1])
items = resp.get("items", [])
actual = [x.get("recommendation_type") for x in items if x.get("recommendation_type")]
actual_set = sorted(set(actual))
passed = len(items) >= 1 and not (len(actual_set) == 1 and actual_set[0] == "unknown")
print(json.dumps({"passed": passed, "actual_types": actual_set, "count": len(items)}, ensure_ascii=False))
' "${response}"
  )"

  passed="$(python3 -c 'import json,sys; print("true" if json.loads(sys.argv[1]).get("passed") else "false")' "${eval_json}")"
  actual_types="$(python3 -c 'import json,sys; print(",".join(json.loads(sys.argv[1]).get("actual_types", [])))' "${eval_json}")"
  parsed_count="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("count", 0))' "${eval_json}")"

  if [[ "${passed}" == "true" ]]; then
    pass_count=$((pass_count + 1))
    printf "  [%02d] PASS count=%s actual={%s}\n" "${idx}" "${parsed_count}" "${actual_types}"
  else
    fail_count=$((fail_count + 1))
    printf "  [%02d] FAIL count=%s actual={%s}\n" "${idx}" "${parsed_count}" "${actual_types}"
  fi

  python3 -c '
import json,sys
record = {
  "case_index": int(sys.argv[1]),
  "input_text": sys.argv[2],
  "evaluation": json.loads(sys.argv[3]),
  "response": json.loads(sys.argv[4]),
}
print(json.dumps(record, ensure_ascii=False))
' "${idx}" "${text}" "${eval_json}" "${response}" >> "${REPORT_JSONL}"
done < "${DATASET_FILE}"

echo "[3/3] Summary"
python3 -c '
import json,sys
payload = {
  "pass": int(sys.argv[1]),
  "fail": int(sys.argv[2]),
  "total": int(sys.argv[3]),
  "pass_rate": (int(sys.argv[1]) / int(sys.argv[3])) if int(sys.argv[3]) else 0.0,
  "jsonl_report": sys.argv[4]
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
with open(sys.argv[5], "w", encoding="utf-8") as f:
  json.dump(payload, f, ensure_ascii=False, indent=2)
' "${pass_count}" "${fail_count}" "${total}" "${REPORT_JSONL}" "${REPORT_SUMMARY_JSON}"
echo "Saved: ${REPORT_JSONL}"
echo "Saved: ${REPORT_SUMMARY_JSON}"

if [[ "${fail_count}" -gt 0 ]]; then
  exit 2
fi
