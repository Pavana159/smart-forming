"""
Crop Recommendation Model Training and Evaluation Pipeline.
Trains and compares Decision Tree and Random Forest classifiers on the Kaggle/ICAR benchmark dataset.
Saves the optimal pipeline and comprehensive evaluation metrics.
"""
import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(CURRENT_DIR, 'data', 'crop_recommendation.csv')
MODEL_FILE = os.path.join(CURRENT_DIR, 'crop_model.joblib')
METRICS_FILE = os.path.join(CURRENT_DIR, 'model_metrics.json')

def train_and_evaluate():
    print(f"Loading dataset from: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE)
    
    features = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
    target = 'label'
    
    X = df[features]
    y = df[target]
    
    # 80-20 Stratified train-test split for unbiased evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # 1. Decision Tree Baseline
    dt_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('dt', DecisionTreeClassifier(random_state=42, max_depth=15, min_samples_split=4))
    ])
    dt_cv_scores = cross_val_score(dt_pipeline, X_train, y_train, cv=cv, scoring='accuracy')
    dt_pipeline.fit(X_train, y_train)
    y_pred_dt = dt_pipeline.predict(X_test)
    
    dt_metrics = {
        'model_name': 'Decision Tree Classifier',
        'cv_mean_accuracy': float(np.mean(dt_cv_scores)),
        'cv_std_accuracy': float(np.std(dt_cv_scores)),
        'test_accuracy': float(accuracy_score(y_test, y_pred_dt)),
        'precision_macro': float(precision_score(y_test, y_pred_dt, average='macro', zero_division=0)),
        'recall_macro': float(recall_score(y_test, y_pred_dt, average='macro', zero_division=0)),
        'f1_macro': float(f1_score(y_test, y_pred_dt, average='macro', zero_division=0))
    }
    
    # 2. Random Forest Classifier
    rf_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('rf', RandomForestClassifier(n_estimators=60, max_depth=16, random_state=42, n_jobs=1))
    ])
    rf_cv_scores = cross_val_score(rf_pipeline, X_train, y_train, cv=cv, scoring='accuracy')
    rf_pipeline.fit(X_train, y_train)
    y_pred_rf = rf_pipeline.predict(X_test)
    
    rf_metrics = {
        'model_name': 'Random Forest Classifier',
        'cv_mean_accuracy': float(np.mean(rf_cv_scores)),
        'cv_std_accuracy': float(np.std(rf_cv_scores)),
        'test_accuracy': float(accuracy_score(y_test, y_pred_rf)),
        'precision_macro': float(precision_score(y_test, y_pred_rf, average='macro', zero_division=0)),
        'recall_macro': float(recall_score(y_test, y_pred_rf, average='macro', zero_division=0)),
        'f1_macro': float(f1_score(y_test, y_pred_rf, average='macro', zero_division=0)),
        'feature_importances': dict(zip(features, [float(x) for x in rf_pipeline.named_steps['rf'].feature_importances_]))
    }
    
    print("\n--- MODEL COMPARISON ---")
    print(f"Decision Tree  - Test Accuracy: {dt_metrics['test_accuracy']*100:.2f}%, F1: {dt_metrics['f1_macro']:.4f}")
    print(f"Random Forest  - Test Accuracy: {rf_metrics['test_accuracy']*100:.2f}%, F1: {rf_metrics['f1_macro']:.4f}")
    
    # Save the superior Random Forest Pipeline
    joblib.dump(rf_pipeline, MODEL_FILE)
    print(f"\nSaved trained Random Forest Pipeline to: {MODEL_FILE}")
    
    # Save evaluation report
    report = {
        'dataset_summary': {
            'total_samples': len(df),
            'features': features,
            'classes': sorted(list(df['label'].unique())),
            'samples_per_class': int(len(df) / len(df['label'].unique()))
        },
        'decision_tree': dt_metrics,
        'random_forest': rf_metrics,
        'selected_model': 'Random Forest Classifier',
        'classification_report': classification_report(y_test, y_pred_rf, output_dict=True)
    }
    
    with open(METRICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"Saved evaluation metrics to: {METRICS_FILE}")
    return report

if __name__ == '__main__':
    train_and_evaluate()
