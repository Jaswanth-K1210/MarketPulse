"""
Task 1.5 — LightGBM + SHAP risk scorer
Replaces hardcoded multipliers in impact_calculator.py.
Trains on synthetic data at startup if no saved model found; retrains
incrementally as confirmed events accumulate in the DB.
"""
import logging
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "models" / "risk_lgbm.pkl"
MODEL_PATH.parent.mkdir(exist_ok=True)

# Feature schema (must match training)
FEATURES = [
    "source_tier",          # 1-4
    "state_affiliated",     # 0/1
    "sentiment_score",      # -1 to 1
    "event_severity",       # 0-3 (none/low/medium/high)
    "supply_chain_depth",   # 1=direct, 2=supplier, 3=customer
    "criticality_score",    # 0-3 (low/medium/high/critical)
    "has_financial_data",   # 0/1
    "article_length",       # 0-3 bucket
    "source_count",         # number of corroborating sources
    "days_since_publish",   # 0-7
]

EVENT_SEVERITY_MAP = {
    "production_halt": 3,
    "factory_fire": 3,
    "natural_disaster": 3,
    "geopolitical_event": 2,
    "supply_chain_disruption": 2,
    "regulatory_action": 2,
    "trade_restriction": 2,
    "chip_shortage": 2,
    "acquisition": 1,
    "partnership": 1,
    "earnings_report": 1,
    "product_launch": 0,
    "technology_breakthrough": 1,
}

CRITICALITY_MAP = {"low": 0, "medium": 1, "high": 2, "critical": 3}
REL_TYPE_MAP = {"direct": 1, "supplier": 2, "customer": 3}


def _make_feature_vector(article_meta: Dict, relationship: Dict, event_type: str = "") -> np.ndarray:
    severity = EVENT_SEVERITY_MAP.get(event_type, 1)
    depth = REL_TYPE_MAP.get(relationship.get("type", "direct"), 1)
    crit = CRITICALITY_MAP.get(relationship.get("criticality", "medium"), 1)
    content_len = len(article_meta.get("content", ""))
    len_bucket = min(int(content_len / 200), 3)
    return np.array([[
        article_meta.get("source_tier", 3),
        int(article_meta.get("state_affiliated", False)),
        float(article_meta.get("sentiment_score", 0.0)),
        severity,
        depth,
        crit,
        int(bool(article_meta.get("has_financial_data", False))),
        len_bucket,
        int(article_meta.get("source_count", 1)),
        int(article_meta.get("days_since_publish", 0)),
    ]], dtype=np.float32)


def _generate_synthetic_training_data(n: int = 2000):
    """Bootstrap training data using domain rules (replaces manual Colab step)."""
    rng = np.random.default_rng(42)
    X, y = [], []
    for _ in range(n):
        tier = rng.integers(1, 5)
        state_aff = rng.integers(0, 2)
        sent = rng.uniform(-1, 1)
        sev = rng.integers(0, 4)
        depth = rng.integers(1, 4)
        crit = rng.integers(0, 4)
        has_fin = rng.integers(0, 2)
        len_b = rng.integers(0, 4)
        src_cnt = rng.integers(1, 6)
        days = rng.integers(0, 8)

        # Domain rule: risk = f(severity, sentiment, tier)
        base = (sev / 3.0) * 0.4 + abs(sent) * 0.3 + ((5 - tier) / 4.0) * 0.15
        base += (crit / 3.0) * 0.1 + (src_cnt / 5.0) * 0.05
        base -= (days / 7.0) * 0.05  # older news = lower risk
        risk = float(np.clip(base + rng.normal(0, 0.05), 0, 1))

        X.append([tier, state_aff, sent, sev, depth, crit, has_fin, len_b, src_cnt, days])
        y.append(risk)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def _train_and_save() -> object:
    try:
        import lightgbm as lgb
    except ImportError:
        logger.warning("lightgbm not installed — risk_scorer will use rule-based fallback")
        return None

    logger.info("Training LightGBM risk scorer on synthetic data...")
    X, y = _generate_synthetic_training_data(3000)
    split = int(len(X) * 0.9)
    model = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        verbose=-1,
    )
    model.fit(
        X[:split], y[:split],
        eval_set=[(X[split:], y[split:])],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(period=-1)],
    )
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info("LightGBM risk scorer trained and saved to %s", MODEL_PATH)
    return model


def _train_and_save_with_feedback(feedback_rows: List[Dict]) -> object:
    """Train LightGBM on a blend of synthetic data and real feedback."""
    try:
        import lightgbm as lgb
    except ImportError:
        logger.warning("lightgbm not installed — cannot train with feedback")
        return None

    X_synth, y_synth = _generate_synthetic_training_data(2000)

    X_fb, y_fb = [], []
    for row in feedback_rows:
        try:
            features_str = row.get("features", "")
            if features_str:
                import json
                features = json.loads(features_str)
                X_fb.append([features.get(f, 0) for f in FEATURES])
                actual = float(row.get("actual_outcome", 0))
                predicted = float(row.get("predicted_risk", 0))
                y_fb.append(float(np.clip((actual + 1) / 2, 0, 1)))
        except Exception:
            continue

    if len(X_fb) < 10:
        logger.info("retrain: only %d valid feedback rows, using synthetic only", len(X_fb))
        X, y = X_synth, y_synth
    else:
        X_fb = np.array(X_fb, dtype=np.float32)
        y_fb = np.array(y_fb, dtype=np.float32)
        n_synth = min(len(X_synth), len(X_fb) * 3)
        indices = np.random.default_rng(42).choice(len(X_synth), n_synth, replace=False)
        X = np.concatenate([X_synth[indices], X_fb])
        y = np.concatenate([y_synth[indices], y_fb])
        logger.info("retrain: blending %d synthetic + %d feedback rows", n_synth, len(X_fb))

    split = int(len(X) * 0.9)
    model = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        verbose=-1,
    )
    model.fit(
        X[:split], y[:split],
        eval_set=[(X[split:], y[split:])],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(period=-1)],
    )
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info("LightGBM risk scorer retrained with feedback, saved to %s", MODEL_PATH)
    return model


class RiskScorer:
    """
    Scores an article's supply-chain risk on [0, 1].
    Uses LightGBM if available, falls back to weighted rule formula.
    Provides SHAP explanations when shap package is installed.
    """

    def __init__(self):
        self._model = None
        self._explainer = None
        self._load_or_train()

    def _load_or_train(self):
        if MODEL_PATH.exists():
            try:
                with open(MODEL_PATH, "rb") as f:
                    self._model = pickle.load(f)
                logger.info("Loaded LightGBM risk scorer from %s", MODEL_PATH)
            except Exception as e:
                logger.warning("Could not load saved model (%s) — retraining", e)
                self._model = _train_and_save()
        else:
            self._model = _train_and_save()

        if self._model is not None:
            try:
                import shap
                self._explainer = shap.TreeExplainer(self._model)
            except (ImportError, Exception) as e:
                logger.debug("SHAP explainer unavailable: %s", e)

    def score(
        self,
        article_meta: Dict,
        relationship: Dict,
        event_type: str = "",
    ) -> Dict:
        """
        Returns {"risk_score": float, "explanation": list[dict]}.
        risk_score in [0, 1] — 0 = no risk, 1 = maximum risk.
        """
        X = _make_feature_vector(article_meta, relationship, event_type)

        if self._model is not None:
            try:
                risk = float(np.clip(self._model.predict(X)[0], 0, 1))
            except Exception as e:
                logger.warning("LightGBM predict failed: %s — using fallback", e)
                risk = self._rule_fallback(article_meta, relationship, event_type)
        else:
            risk = self._rule_fallback(article_meta, relationship, event_type)

        explanation = self._explain(X, risk)
        return {"risk_score": round(risk, 4), "explanation": explanation}

    def _rule_fallback(self, article_meta: Dict, relationship: Dict, event_type: str) -> float:
        sev = EVENT_SEVERITY_MAP.get(event_type, 1) / 3.0
        sent = abs(float(article_meta.get("sentiment_score", 0.0)))
        tier_w = (5 - int(article_meta.get("source_tier", 3))) / 4.0
        crit = CRITICALITY_MAP.get(relationship.get("criticality", "medium"), 1) / 3.0
        return float(np.clip(sev * 0.4 + sent * 0.3 + tier_w * 0.2 + crit * 0.1, 0, 1))

    def _explain(self, X: np.ndarray, risk: float) -> List[Dict]:
        if self._explainer is not None:
            try:
                shap_vals = self._explainer.shap_values(X)[0]
                return [
                    {"feature": FEATURES[i], "impact": round(float(shap_vals[i]), 4)}
                    for i in np.argsort(np.abs(shap_vals))[::-1][:5]
                ]
            except Exception:
                pass
        # Fallback: return feature values without SHAP
        return [{"feature": FEATURES[i], "value": round(float(X[0][i]), 3)} for i in range(len(FEATURES))]

    def retrain(self, feedback_rows: Optional[List[Dict]] = None):
        """Incorporate confirmed event outcomes into the risk scorer model.

        If feedback_rows is provided, those are used directly.
        Otherwise, unincorporated feedback is pulled from the database.
        """
        if feedback_rows is None:
            try:
                from app.services.database import get_unincorporated_feedback, mark_feedback_incorporated
                db_rows = get_unincorporated_feedback(min_rows=50)
                if len(db_rows) < 50:
                    logger.info("retrain: only %d feedback rows (need 50), skipping", len(db_rows))
                    return
                feedback_rows = db_rows
            except Exception as e:
                logger.warning("retrain: could not load feedback from DB: %s", e)
                return

        if not feedback_rows:
            logger.info("retrain: no feedback rows, skipping")
            return

        try:
            self._model = _train_and_save_with_feedback(feedback_rows)
        except Exception as e:
            logger.warning("retrain: training with feedback failed: %s, falling back to synthetic", e)
            self._model = _train_and_save()

        if self._model is not None:
            try:
                import shap
                self._explainer = shap.TreeExplainer(self._model)
            except (ImportError, Exception):
                pass

        try:
            from app.services.database import mark_feedback_incorporated
            row_ids = [r["id"] for r in feedback_rows if "id" in r]
            mark_feedback_incorporated(row_ids)
            logger.info("retrain: incorporated %d feedback rows", len(row_ids))
        except Exception as e:
            logger.warning("retrain: could not mark feedback as incorporated: %s", e)


# Singleton
risk_scorer = RiskScorer()
