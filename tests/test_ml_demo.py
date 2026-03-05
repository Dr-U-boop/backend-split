import pytest

from app.recommendation_extraction.ml import MLTypeClassifier, tiny_training_dataset


def test_ml_demo_train_predict():
    sklearn = pytest.importorskip("sklearn")
    assert sklearn is not None

    texts, labels = tiny_training_dataset()
    model = MLTypeClassifier().train(texts, labels)
    label, score = model.predict("врем базал -25%")
    assert label == "temp_basal_percent"
    assert score >= 0.3

