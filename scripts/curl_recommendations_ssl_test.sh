#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://194.58.95.112}"
LOGIN_PATH="${LOGIN_PATH:-/api/auth/login}"
INTERPRET_PATH="${INTERPRET_PATH:-/api/recommendations/interpret}"
USERNAME="${USERNAME:-doctor}"
PASSWORD="${PASSWORD:-supersecretpassword123}"
INSECURE_TLS="${INSECURE_TLS:-1}"

if [[ "${INSECURE_TLS}" == "1" ]]; then
  CURL_TLS_FLAG="--insecure"
else
  CURL_TLS_FLAG=""
fi

echo "[1/3] Login: ${BASE_URL}${LOGIN_PATH}"
LOGIN_RESP="$(
  curl -sS ${CURL_TLS_FLAG} -X POST "${BASE_URL}${LOGIN_PATH}" \
    -H "Content-Type: application/json" \
    --data "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"

TOKEN="$(printf '%s' "${LOGIN_RESP}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null || true)"
if [[ -z "${TOKEN}" ]]; then
  echo "ERROR: cannot parse access_token from login response"
  echo "Login response: ${LOGIN_RESP}"
  exit 1
fi
echo "Token acquired."

echo "[2/3] Run recommendation tests"

declare -a CASES=(
  "basal_rate|Изменить базальную скорость до 0.80 Ед/ч в период 23:00-02:00"
  "basal_rate|базал 0,8 ед/ч с 23 до 2"
  "carb_ratio|угл коэф 1ед/10гр с 6 до 11"
  "correction_factor|фактор чуствит 1eд/2,2 ммольл ночью"
  "target_range|целевой диапазон 5.5-7.0 ммоль/л днем"
  "target_glucose|таргет 6.4 ммоль/л ночью"
  "prebolus_time|предболюс за 15 мин утром"
  "temp_basal_percent|врем базал -20 проц при нагр вечером"
  "active_insulin_time|активный инсулин 4 часа"
  "correction_interval|не корригировать раньше 3 ч после предыдущего болюса"
  "low_glucose_alert_threshold|низкий порог 3.9"
  "high_glucose_alert_threshold|высокий порог 11.2"
  "dual_bolus_split|60% сразу и 40% за 2 часа на ужин"
)

pass_count=0
fail_count=0
idx=0

for case_item in "${CASES[@]}"; do
  idx=$((idx + 1))
  expected="${case_item%%|*}"
  text="${case_item#*|}"

  response="$(
    curl -sS ${CURL_TLS_FLAG} -X POST "${BASE_URL}${INTERPRET_PATH}" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}, ensure_ascii=False))' "${text}")"
  )"

  actual="$(printf '%s' "${response}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("recommendation_type",""))' 2>/dev/null || true)"

  if [[ "${actual}" == "${expected}" ]]; then
    pass_count=$((pass_count + 1))
    printf "  [%02d] PASS  expected=%s text=%s\n" "${idx}" "${expected}" "${text}"
  else
    fail_count=$((fail_count + 1))
    printf "  [%02d] FAIL  expected=%s actual=%s text=%s\n" "${idx}" "${expected}" "${actual}" "${text}"
    printf "       response=%s\n" "${response}"
  fi
done

echo "[3/3] Summary"
echo "PASS=${pass_count} FAIL=${fail_count} TOTAL=${#CASES[@]}"

if [[ "${fail_count}" -gt 0 ]]; then
  exit 2
fi

