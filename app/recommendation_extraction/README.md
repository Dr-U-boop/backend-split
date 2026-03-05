# Recommendation Extraction Pipeline

## 1. Краткий план рефакторинга
1. Убрать зависимость от хрупкого `spacy.Matcher`-only парсинга.
2. Ввести каскад: `normalization -> fuzzy dictionaries -> rule extraction -> ML fallback -> domain validation`.
3. Добавить прозрачный `confidence` + `trace` + `errors_or_warnings`.
4. Оставить совместимый API: `parse_recommendation_text`.
5. Покрыть грязные русскоязычные кейсы unit-тестами.

## 2. Структура модулей
```text
app/recommendation_extraction/
  __init__.py
  schemas.py
  dictionaries.py
  normalization.py
  fuzzy_match.py
  patterns.py
  validation.py
  ml.py
  extractor.py
app/recommendation_parser.py   # backward-compatible facade
tests/
  test_normalization.py
  test_recommendation_extractor.py
  test_ml_demo.py
```

## 3. API
```python
from app.recommendation_extraction.extractor import parse_recommendation, parse_batch

result = parse_recommendation("базал 0,8 ед/ч с 23 до 2")
batch = parse_batch(["предболюс 15 мин", "порог высокой глюкозы 10"])
```

`result`:
- `recommendation_type`
- `text`
- `normalized_text`
- `value`, `value_min`, `value_max`
- `unit`
- `time_start`, `time_end`
- `condition`
- `confidence`
- `parse_method`
- `errors_or_warnings`
- `trace`

## 4. Легкий ML fallback
`ml.py` содержит CPU-friendly классификатор:
- `TfidfVectorizer(word 1-2 grams + char 3-5 grams)`
- `LogisticRegression`

Пример:
```python
from app.recommendation_extraction.ml import train_demo_model
metrics = train_demo_model("app/recommendation_extraction/demo_type_classifier.joblib")
print(metrics["classification_report"])
```

ML включается только при низкой уверенности rule-based слоя (`ParseConfig.enable_ml_fallback=True`).

## 5. Метрики и оценивание
Минимально рекомендуется считать:
- `type_accuracy` (правильный `recommendation_type`)
- `value_mae` для числовых сущностей
- `range_exact_match` для `target_range`
- `time_interval_exact_match`
- `unit_accuracy`
- `warning_rate` (доля записей с предупреждениями)

Пример baseline-оценки:
1. Собрать валидированный CSV (`text`, `type`, `value`, `unit`, `time_start`, `time_end`).
2. Прогнать `parse_batch`.
3. Сравнить поля по типу сущности (можно использовать `evaluation.py::evaluate_predictions`).

## 6. Конфигурируемость словарей
Изменяемые словари:
- `RECOMMENDATION_ALIASES`
- `COMMON_TYPO_REPLACEMENTS`
- `CONDITION_ALIASES`
- `UNIT_NORMALIZATION_RULES`

Можно расширять без изменения core-алгоритма.

## 7. Почему это production-ready
- Без тяжелых трансформеров по умолчанию.
- Полностью CPU-friendly.
- Интерпретируемые правила + трассировка (`trace`).
- Fuzzy + typo-tolerant слой снижает чувствительность к ошибкам врача/OCR.
- Явная domain validation для раннего обнаружения некорректных комбинаций.
