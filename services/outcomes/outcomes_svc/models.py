"""Predictive models — placement success + offer acceptance.

scikit-learn LogisticRegression because:
- Tiny model footprint (~ few KB serialized)
- Linear model = explainable per-feature coefficients
- Trains in under a second on a 1500-row synthetic set
- Probabilistic output (predict_proba) is what the platform wants

Model files are written to disk under ./models/ so the FastAPI service
can hot-reload them without retraining.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import structlog
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from outcomes_svc.features import (
    OFFER_ACCEPTANCE_FEATURES,
    PLACEMENT_FEATURES,
    FeatureRow,
    to_feature_matrix,
    to_label_vector,
)

log = structlog.get_logger("outcomes.models")


MODEL_DIR = Path(os.environ.get("WFI_MODEL_DIR", "./models"))


@dataclass
class TrainResult:
    feature_set: str
    n_train: int
    n_test: int
    train_accuracy: float
    test_accuracy: float
    test_auc: float
    coefficients: dict[str, float]
    intercept: float
    trained_at: float = field(default_factory=time.time)


@dataclass
class Predictor:
    feature_set: str
    feature_names: list[str]
    scaler: StandardScaler
    model: LogisticRegression

    def predict_proba(self, features: dict[str, float]) -> float:
        vector = [[float(features.get(name, 0.0)) for name in self.feature_names]]
        scaled = self.scaler.transform(vector)
        return float(self.model.predict_proba(scaled)[0][1])

    def explain(self, features: dict[str, float]) -> dict[str, float]:
        vector = [float(features.get(name, 0.0)) for name in self.feature_names]
        scaled = self.scaler.transform([vector])[0]
        contributions: dict[str, float] = {}
        for name, scaled_value, coef in zip(self.feature_names, scaled, self.model.coef_[0]):
            contributions[name] = round(float(scaled_value * coef), 4)
        return contributions


def train(
    rows: list[FeatureRow], *, feature_names: list[str], feature_set: str,
    test_size: float = 0.2, seed: int = 0,
) -> tuple[Predictor, TrainResult]:
    if not rows:
        raise ValueError("no training rows supplied")
    X = to_feature_matrix(rows, feature_names)
    y = to_label_vector(rows)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y if len(set(y)) > 1 else None,
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = LogisticRegression(max_iter=400, class_weight="balanced", random_state=seed)
    model.fit(X_train_s, y_train)

    train_acc = accuracy_score(y_train, model.predict(X_train_s))
    test_acc = accuracy_score(y_test, model.predict(X_test_s))
    try:
        test_auc = roc_auc_score(y_test, model.predict_proba(X_test_s)[:, 1])
    except ValueError:
        test_auc = float("nan")

    coefs = {name: round(float(c), 4) for name, c in zip(feature_names, model.coef_[0])}
    result = TrainResult(
        feature_set=feature_set,
        n_train=len(y_train),
        n_test=len(y_test),
        train_accuracy=round(float(train_acc), 4),
        test_accuracy=round(float(test_acc), 4),
        test_auc=round(float(test_auc), 4) if test_auc == test_auc else 0.0,
        coefficients=coefs,
        intercept=round(float(model.intercept_[0]), 4),
    )
    return Predictor(
        feature_set=feature_set,
        feature_names=feature_names,
        scaler=scaler,
        model=model,
    ), result


def save(predictor: Predictor, name: str | None = None) -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / f"{name or predictor.feature_set}.joblib"
    joblib.dump(predictor, path)
    log.info("model_saved", path=str(path))
    return path


def load(name: str) -> Predictor:
    path = MODEL_DIR / f"{name}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"model not found: {path}")
    return joblib.load(path)


def train_placement_model(rows: list[FeatureRow]) -> tuple[Predictor, TrainResult]:
    return train(rows, feature_names=PLACEMENT_FEATURES, feature_set="placement_success")


def train_offer_acceptance_model(rows: list[FeatureRow]) -> tuple[Predictor, TrainResult]:
    return train(rows, feature_names=OFFER_ACCEPTANCE_FEATURES, feature_set="offer_acceptance")
