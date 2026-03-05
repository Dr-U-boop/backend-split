from __future__ import annotations

from dataclasses import dataclass

from app.recommendation_extraction.schemas import RecommendationType

try:
    from joblib import dump, load
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report
    from sklearn.pipeline import FeatureUnion, Pipeline
except Exception:  # pragma: no cover
    dump = None
    load = None
    TfidfVectorizer = None
    LogisticRegression = None
    FeatureUnion = None
    Pipeline = None
    classification_report = None


SUPPORTED_TYPES: list[RecommendationType] = [
    "basal_rate",
    "carb_ratio",
    "correction_factor",
    "target_glucose",
    "target_range",
    "prebolus_time",
    "temp_basal_percent",
    "active_insulin_time",
    "dual_bolus_split",
    "correction_interval",
    "low_glucose_alert_threshold",
    "high_glucose_alert_threshold",
]


@dataclass(slots=True)
class MLTypeClassifier:
    pipeline: object | None = None

    def available(self) -> bool:
        return self.pipeline is not None

    def train(self, texts: list[str], labels: list[RecommendationType]) -> "MLTypeClassifier":
        if Pipeline is None:
            raise RuntimeError("scikit-learn is not available")
        vectorizer = FeatureUnion(
            transformer_list=[
                ("word", TfidfVectorizer(ngram_range=(1, 2), analyzer="word", min_df=1)),
                ("char", TfidfVectorizer(ngram_range=(3, 5), analyzer="char_wb", min_df=1)),
            ]
        )
        clf = LogisticRegression(max_iter=1200, n_jobs=1, class_weight="balanced")
        self.pipeline = Pipeline([("features", vectorizer), ("clf", clf)])
        self.pipeline.fit(texts, labels)
        return self

    def predict(self, text: str) -> tuple[RecommendationType, float]:
        if self.pipeline is None:
            return "unknown", 0.0
        label = self.pipeline.predict([text])[0]
        if hasattr(self.pipeline, "predict_proba"):
            probs = self.pipeline.predict_proba([text])[0]
            classes = list(self.pipeline.classes_)
            idx = classes.index(label)
            return label, float(probs[idx])
        return label, 0.55

    def save(self, path: str) -> None:
        if dump is None:
            raise RuntimeError("joblib is not available")
        if self.pipeline is None:
            raise RuntimeError("Model not trained")
        dump(self.pipeline, path)

    @classmethod
    def load(cls, path: str) -> "MLTypeClassifier":
        if load is None:
            raise RuntimeError("joblib is not available")
        return cls(pipeline=load(path))


def tiny_training_dataset() -> tuple[list[str], list[RecommendationType]]:
    rows: list[tuple[str, RecommendationType]] = [
        ("базал 0.8 ед/ч с 23 до 2", "basal_rate"),
        ("базальная скорость 1.0 ед/ч ночью", "basal_rate"),
        ("угл коэф 1 ед/9 г утром", "carb_ratio"),
        ("углеводный коэффициент 1ед/10г", "carb_ratio"),
        ("фактор чувствительности 1ед/2.2 ммоль/л", "correction_factor"),
        ("чувствительность 1 ед/3 ммоль/л", "correction_factor"),
        ("целевой диапазон 5.5-7.0 ммоль/л", "target_range"),
        ("целевая глюкоза 6.2 ммоль/л", "target_glucose"),
        ("предболюс 15 мин до еды", "prebolus_time"),
        ("врем базал -20% при нагрузке", "temp_basal_percent"),
        ("активный инсулин 4 ч", "active_insulin_time"),
        ("не корректировать раньше 3 ч", "correction_interval"),
        ("порог низкой глюкозы 4.4", "low_glucose_alert_threshold"),
        ("порог высокой глюкозы 10", "high_glucose_alert_threshold"),
        ("60% сразу и 40% за 2 часа", "dual_bolus_split"),
    ]
    texts = [r[0] for r in rows]
    labels = [r[1] for r in rows]
    return texts, labels


def train_demo_model(model_path: str) -> dict:
    texts, labels = tiny_training_dataset()
    model = MLTypeClassifier().train(texts, labels)
    if model_path:
        model.save(model_path)
    metrics = {}
    if classification_report is not None:
        y_pred = [model.predict(t)[0] for t in texts]
        metrics["classification_report"] = classification_report(labels, y_pred, zero_division=0)
    return metrics

