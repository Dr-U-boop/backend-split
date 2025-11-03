# backend/app/recommendation_parser.py
import spacy
from spacy.matcher import Matcher

# Загружаем малую русскую модель. Она быстрая и работает на CPU.
nlp = spacy.load("ru_core_news_sm")

# Инициализируем Matcher
matcher = Matcher(nlp.vocab)

# --- 1. ОПРЕДЕЛЯЕМ НАШИ ШАБЛОНЫ ---

# Шаблон 1: Изменение базального инсулина (например, "снизить базу на 10 %")
pattern_basal = [
    # "снизить", "повысить", "увеличить", "уменьшить"
    {"LEMMA": {"IN": ["снизить", "повысить", "увеличить", "уменьшить"]}},
    # "базу", "базальный"
    {"LEMMA": {"IN": ["база", "базальный"]}},
    # "на"
    {"LOWER": "на"},
    # число (10, 15, 20.5)
    {"LIKE_NUM": True},
    # "%"
    {"LOWER": "%"}
]

# Шаблон 2: Установка углеводного коэффициента (например, "УК на завтрак 1:10")
pattern_carb_ratio = [
    # "УК" или "коэффициент"
    {"LOWER": {"IN": ["ук", "коэффициент"]}},
    # "на"
    {"LOWER": "на"},
    # "завтрак", "обед", "ужин"
    {"LEMMA": {"IN": ["завтрак", "обед", "ужин"]}},
    # число (1:10 -> нам нужно 10)
    {"IS_PUNCT": True, "OP": "?"}, # Опциональное двоеточие или 1:
    {"LIKE_NUM": True}
]

pattern_time_segment = [
    {"LOWER": {"IN": ["с", "от"]}},
    # Ищем токен, который похож на время (dd:dd, d:dd, dd.dd, d.dd)
    {"SHAPE": {"IN": ["dd:dd", "d:dd", "dd.dd", "d.dd"]}}, 
    {"LOWER": {"IN": ["до", "по"]}},
    {"SHAPE": {"IN": ["dd:dd", "d:dd", "dd.dd", "d.dd"]}}
]

matcher.add("TIME_SEGMENT", [pattern_time_segment])

# Добавляем шаблоны в Matcher
matcher.add("BASAL_CHANGE", [pattern_basal])
matcher.add("CARB_RATIO_CHANGE", [pattern_carb_ratio])


# --- 2. ФУНКЦИЯ-ПАРСЕР ---

def parse_recommendation_text(text: str) -> dict:
    """
    Парсит текстовую рекомендацию и возвращает структурированный JSON, 
    включая поиск временного сегмента.
    """
    # Приводим к нижнему регистру для надежности
    doc = nlp(text.lower()) 
    matches = matcher(doc)

    results = {
        "basal_changes": [],
        "carb_ratio_changes": [],
        "correction_factor_changes": []
    }
    
    time_segment_found = None
    
    # --- ЭТАП 1: Поиск временного сегмента (Контекст) ---
    # Сначала ищем, не указан ли временной сегмент, который будет применен ко всем изменениям базы.
    for match_id, start, end in matches:
        rule_id = nlp.vocab.strings[match_id]
        
        if rule_id == "TIME_SEGMENT":
            span = doc[start:end]
            # span[1] - первое время, span[3] - второе время
            
            # 1. Заменяем точки на двоеточия (e.g., "23.00" -> "23:00")
            time1_raw = span[1].text.replace('.', ':')
            time2_raw = span[3].text.replace('.', ':')
            
            # 2. Добавляем ведущий ноль, если его нет (e.g., "6:00" -> "06:00")
            # zfill(5) идеально подходит для формата "ЧЧ:ММ" (5 символов)
            time1 = time1_raw.zfill(5)
            time2 = time2_raw.zfill(5)
            
            time_segment_found = f"{time1}-{time2}"
            
            # Нашли, что искали. Прерываем цикл поиска времени.
            break 

    # --- ЭТАП 2: Поиск и обработка самих изменений (Действия) ---
    for match_id, start, end in matches:
        span = doc[start:end]
        rule_id = nlp.vocab.strings[match_id]

        if rule_id == "BASAL_CHANGE":
            action_token = span[0]  # "снизить", "повысить"
            value_token = span[3]  # "10", "20"
            
            # .text.replace(',', '.') handles "20,5"
            value = float(value_token.text.replace(',', '.'))
            if action_token.lemma_ in ["снизить", "уменьшить"]:
                value = -value
                
            results["basal_changes"].append({
                # Применяем найденный контекст времени или значение по умолчанию
                "time_segment": time_segment_found or "00:00-24:00", 
                "change_percent": value
            })

        if rule_id == "CARB_RATIO_CHANGE":
            meal_token = span[2]   # "завтрак", "обед"
            value_token = span[-1] # последнее число (10, 15)
            
            results["carb_ratio_changes"].append({
                "meal_time": meal_token.lemma_,
                "value": float(value_token.text.replace(',', '.'))
            })

    return results