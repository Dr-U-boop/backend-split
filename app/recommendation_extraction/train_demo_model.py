from __future__ import annotations

from app.recommendation_extraction.ml import train_demo_model


if __name__ == "__main__":
    metrics = train_demo_model("app/recommendation_extraction/demo_type_classifier.joblib")
    report = metrics.get("classification_report")
    if report:
        print(report)
    print("Saved demo model to app/recommendation_extraction/demo_type_classifier.joblib")

