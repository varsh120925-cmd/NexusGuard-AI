"""
NexusGuard Machine Learning Training, Comparison & Evaluation Pipeline
Trains, evaluates, and compares multiple classifiers on the logistics risk dataset,
fits the Isolation Forest anomaly detector, and persists production artifacts.
"""

import json
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, IsolationForest
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

from app.ml.preprocessor import (
    build_preprocessor_pipeline,
    prepare_features_df,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES
)

def train_and_evaluate_models(dataset_path=None, output_dir=None):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if dataset_path is None:
        dataset_path = os.path.join(base_dir, "dataset", "logistics_risk_dataset.csv")
    if output_dir is None:
        output_dir = os.path.join(base_dir, "trained_models")

    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading dataset from: {dataset_path}")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at: {dataset_path}")

    raw_df = pd.read_csv(dataset_path)
    print(f"Loaded {len(raw_df)} rows and {len(raw_df.columns)} columns.")

    # Prepare features
    X_df = prepare_features_df(raw_df)
    y = raw_df["is_delayed_risk"].astype(int)

    # Stratified Train/Test Split (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X_df, y, test_size=0.20, stratify=y, random_state=42
    )

    print(f"Training set: {len(X_train)} samples | Testing set: {len(X_test)} samples")

    # Fit Preprocessor Pipeline
    print("Fitting preprocessing & feature engineering pipeline...")
    preprocessor = build_preprocessor_pipeline()
    X_train_trans = preprocessor.fit_transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    # Candidate Models
    models = {
        "Random Forest Classifier": RandomForestClassifier(
            n_estimators=120, max_depth=12, min_samples_split=4, random_state=42, n_jobs=-1
        ),
        "Gradient Boosting Classifier": GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42
        ),
        "Decision Tree Classifier": DecisionTreeClassifier(
            max_depth=8, min_samples_split=6, random_state=42
        ),
        "Logistic Regression": LogisticRegression(
            max_iter=1000, random_state=42
        )
    }

    comparison_results = {}
    best_model_name = None
    best_f1 = -1.0
    best_model_obj = None

    print("\n--- Training and Evaluating Classification Models ---")
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train_trans, y_train)

        # Predictions
        y_pred = model.predict(X_test_trans)
        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(X_test_trans)[:, 1]
            auc = round(float(roc_auc_score(y_test, y_proba)), 4)
        else:
            auc = 0.0

        acc = round(float(accuracy_score(y_test, y_pred)), 4)
        prec = round(float(precision_score(y_test, y_pred, zero_division=0)), 4)
        rec = round(float(recall_score(y_test, y_pred, zero_division=0)), 4)
        f1 = round(float(f1_score(y_test, y_pred, zero_division=0)), 4)
        cm = confusion_matrix(y_test, y_pred).tolist()

        comparison_results[name] = {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "roc_auc": auc,
            "confusion_matrix": cm
        }

        print(f"  {name} -> Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f} | ROC-AUC: {auc:.4f}")

        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            best_model_obj = model

    print(f"\nOptimal Model Selected: {best_model_name} (F1 Score: {best_f1:.4f})")

    # Fit Isolation Forest for Anomaly Detection
    print("\nFitting Isolation Forest for Unsupervised Anomaly Detection...")
    anomaly_feature_cols = [
        "shipment_value_usd", "weight_kg", "distance_km",
        "transit_stops", "carrier_historical_delay_rate", "weather_severity_index"
    ]
    iso_forest = IsolationForest(
        n_estimators=150, contamination=0.05, max_samples="auto", random_state=42, n_jobs=-1
    )
    # Fit on training data numerical features
    iso_forest.fit(X_train[anomaly_feature_cols])

    # Extract Feature Importances from the best model (if tree-based)
    feature_names = []
    # Numeric feature names
    feature_names.extend(NUMERICAL_FEATURES)
    # Categorical one-hot feature names
    onehot_trans = preprocessor.named_steps["preprocessor"].named_transformers_["cat"].named_steps["onehot"]
    cat_feature_names = onehot_trans.get_feature_names_out(CATEGORICAL_FEATURES)
    feature_names.extend(cat_feature_names)

    feature_importances = {}
    if hasattr(best_model_obj, "feature_importances_"):
        importances = best_model_obj.feature_importances_
        for f_name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
            feature_importances[f_name] = round(float(imp), 4)

    # Save artifacts
    model_save_path = os.path.join(output_dir, "logistics_risk_rf_model.joblib")
    preproc_save_path = os.path.join(output_dir, "preprocessor.joblib")
    iso_save_path = os.path.join(output_dir, "isolation_forest_anomaly.joblib")
    metrics_save_path = os.path.join(output_dir, "model_metrics.json")

    joblib.dump(best_model_obj, model_save_path)
    joblib.dump(preprocessor, preproc_save_path)
    joblib.dump(iso_forest, iso_save_path)

    metrics_payload = {
        "best_model": best_model_name,
        "evaluation_metrics": comparison_results[best_model_name],
        "all_models_comparison": comparison_results,
        "feature_importances": feature_importances,
        "feature_count": len(feature_names),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "anomaly_features": anomaly_feature_cols
    }

    with open(metrics_save_path, "w") as f:
        json.dump(metrics_payload, f, indent=2)

    print(f"\nProduction Artifacts Successfully Saved:")
    print(f"  Classification Model: {model_save_path}")
    print(f"  Preprocessing Pipeline: {preproc_save_path}")
    print(f"  Anomaly Model: {iso_save_path}")
    print(f"  Metrics & Comparison: {metrics_save_path}")

    return metrics_payload

if __name__ == "__main__":
    train_and_evaluate_models()
