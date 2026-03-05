| ? | PASS | Expected | Actual | Value | Unit | Time | Condition | Confidence | Method | Text |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | OK | basal_rate | basal_rate | 0.8 | Ед/ч | 23:00-02:00 |  | 0.9707 | hybrid | Изменить базальную скорость до 0.80 Ед/ч в период 23:00-02:00 |
| 2 | OK | basal_rate | basal_rate | 0.8 | Ед/ч | 23:00-02:00 |  | 1.0 | hybrid | базал 0,8 ед/ч с 23 до 2 |
| 3 | OK | carb_ratio | carb_ratio | 10.0 | г/Ед | 06:00-11:00 |  | 0.9158 | hybrid | угл коэф 1ед/10гр с 6 до 11 |
| 4 | OK | correction_factor | correction_factor | 2.2 | ммоль/л/Ед |  | ночью | 0.8457 | hybrid | фактор чуствит 1eд/2,2 ммольл ночью |
| 5 | OK | target_range | target_range | 5.5..7.0 | ммоль/л |  | днем | 0.9851 | hybrid | целевой диапазон 5.5-7.0 ммоль/л днем |
| 6 | OK | target_glucose | target_glucose | 6.4 | ммоль/л |  | ночью | 0.9798 | hybrid | таргет 6.4 ммоль/л ночью |
| 7 | OK | prebolus_time | prebolus_time | 15.0 | мин |  | утром | 0.9827 | hybrid | предболюс за 15 мин утром |
| 8 | OK | temp_basal_percent | temp_basal_percent | -20.0 | % |  | вечером | 0.9257 | rule_regex | врем базал -20 проц при нагр вечером |
| 9 | OK | active_insulin_time | active_insulin_time | 4.0 | ч |  |  | 0.94 | hybrid | активный инсулин 4 часа |
| 10 | OK | correction_interval | correction_interval | 3.0 | ч |  |  | 0.8405 | hybrid | не корригировать раньше 3 ч после предыдущего болюса |
| 11 | OK | low_glucose_alert_threshold | low_glucose_alert_threshold | 3.9 | ммоль/л |  |  | 0.94 | hybrid | низкий порог 3.9 |
| 12 | OK | high_glucose_alert_threshold | high_glucose_alert_threshold | 11.2 | ммоль/л |  |  | 0.94 | hybrid | высокий порог 11.2 |
| 13 | OK | dual_bolus_split | dual_bolus_split | 60.0%/40.0% | %/% + ч |  | вечером | 0.9784 | hybrid | 60% сразу и 40% за 2 часа на ужин |
