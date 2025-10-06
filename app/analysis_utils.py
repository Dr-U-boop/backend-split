# backend/app/analysis_utils.py
from datetime import time, timedelta

def analyze_patient_data(all_records: list) -> list:
    recommendations = []
    # Разделяем данные по типам для удобства анализа
    glucose_records = [r for r in all_records if r['record_type'] == 'glucose']
    carb_records = [r for r in all_records if r['record_type'] == 'carbs']
    
    
    # --- Правило 1: Поиск ночных гипогликемий ---
    night_lows = 0
    for record in glucose_records:
        record_time = record["timestamp"].time()
        # Ночное время с 00:00 до 06:00
        if time(0, 0) <= record_time < time(6, 0):
            if record["value"] < 4.0: # Порог гипогликемии
                night_lows += 1
    
    if night_lows > 2: # Если было больше 2 случаев за период
        recommendations.append(
            "⚠️ Обнаружены повторяющиеся ночные гипогликемии. "
            "Рекомендуется рассмотреть коррекцию вечерней дозы базального инсулина."
        )

    # --- Правило 2: Поиск постпрандиальных (после еды) пиков ---
    post_meal_spikes = 0
    # (Это упрощенная симуляция, т.к. у нас нет данных о приемах пищи.
    # Мы ищем пики в типичное время после еды)
    for record in glucose_records:
        record_time = record["timestamp"].time()
        if time(10, 0) <= record_time < time(12, 0) or \
           time(15, 0) <= record_time < time(17, 0) or \
           time(20, 0) <= record_time < time(22, 0):
            if record["value"] > 10.0: # Порог гипергликемии
                post_meal_spikes += 1
    
    for meal in carb_records:
        # Ищем показания глюкозы через ~2 часа после еды
        two_hours_after = meal['timestamp'] + timedelta(hours=2)
        relevant_glucose_readings = [
            g['value'] for g in glucose_records 
            if meal['timestamp'] < g['timestamp'] <= two_hours_after
        ]
        
        if relevant_glucose_readings:
            peak_glucose = max(relevant_glucose_readings)
            if peak_glucose > 10.0: # Постпрандиальная гипергликемия
                meal_time = meal['timestamp'].strftime('%d.%m %H:%M')
                recommendations.append(
                    f"📈 Обнаружен высокий пик глюкозы ({peak_glucose} ммоль/л) после приема пищи в {meal_time}. "
                    "Возможно, углеводный коэффициент для этого приема пищи нуждается в коррекции."
                )
                break # Достаточно одного примера, чтобы не спамить

    if not recommendations:
        recommendations.append("✅ Комплексный анализ не выявил явных отклонений.")

    return recommendations