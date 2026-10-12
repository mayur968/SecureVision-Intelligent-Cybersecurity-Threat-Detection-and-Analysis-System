"""
Train APK malware detection model.

Generates synthetic training data that matches the full 44-feature
vector produced by APKFeatureExtractor.get_feature_vector(), then
trains a Random Forest + Logistic Regression ensemble and saves the
best model to models/apk_model.pkl.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score,
                              recall_score, f1_score, classification_report)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from features.apk_features import APKFeatureExtractor
from config import Config


def generate_synthetic_apk_data(n_safe: int = 200, n_malicious: int = 200,
                                  seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic APK feature data that matches the 44-feature vector.
    
    Safe APKs:     low permissions, few dangerous perms, no suspicious APIs
    Malicious APKs: high dangerous perms, suspicious APIs, obfuscation, etc.
    """
    rng = np.random.default_rng(seed)
    extractor = APKFeatureExtractor()
    feature_names = extractor.get_feature_names()
    n_features = len(feature_names)

    rows = []

    # ── Safe APKs ────────────────────────────────────────────────────────────
    for _ in range(n_safe):
        perm_count     = int(rng.integers(3, 15))
        dangerous      = int(rng.integers(0, 3))
        row = [
            perm_count,                         # permission_count
            dangerous,                          # dangerous_permission_count
            round(dangerous / max(perm_count, 1), 3),  # dangerous_permission_ratio
            0,                                  # has_sms_permissions
            0,                                  # has_phone_permissions
            int(rng.integers(0, 2)),            # has_location_permissions
            int(rng.integers(0, 2)),            # has_storage_permissions
            0,                                  # has_admin_permissions
            1,                                  # has_internet
            round(float(rng.uniform(1.0, 2.5)), 3),  # permission_entropy
            int(rng.integers(3, 12)),           # activity_count
            int(rng.integers(0, 3)),            # service_count
            int(rng.integers(0, 2)),            # receiver_count
            int(rng.integers(0, 2)),            # provider_count
            int(rng.integers(4, 18)),           # component_count
            int(rng.integers(0, 3)),            # exported_activity_count
            0,                                  # exported_service_count
            0,                                  # exported_receiver_count
            0,                                  # suspicious_receiver_count
            int(rng.integers(1, 5)),            # intent_filter_count
            1,                                  # dex_count
            0,                                  # has_reflection_api
            0,                                  # has_dynamic_code_loading
            int(rng.integers(0, 2)),            # has_crypto_api
            0,                                  # has_runtime_exec
            0,                                  # has_native_code_loading
            0,                                  # suspicious_api_count
            0,                                  # api_diversity_score
            0,                                  # cert_is_debug
            1,                                  # cert_is_valid
            round(float(rng.uniform(0.5, 3.0)), 3),  # cert_validity_days_norm
            0,                                  # cert_self_signed
            round(float(rng.uniform(0.05, 0.3)), 3),  # file_count_normalized
            int(rng.integers(0, 2)),            # has_native_libs
            int(rng.integers(0, 2)),            # native_lib_count
            0,                                  # is_obfuscated
            0,                                  # manifest_anomaly_count
            0,                                  # suspicious_string_count
            0,                                  # has_url_strings
            0,                                  # has_ip_strings
            int(dangerous > 0),                 # has_dangerous_permissions (legacy)
            round(float(rng.uniform(0.05, 0.3)), 3),  # file_count_normalized_compat
            1,                                  # dex_count_compat
            int(rng.integers(0, 2)),            # has_native_libs_compat
        ]
        rows.append(row + [0])  # label = 0 (safe)

    # ── Malicious APKs ───────────────────────────────────────────────────────
    for _ in range(n_malicious):
        perm_count  = int(rng.integers(15, 40))
        dangerous   = int(rng.integers(8, min(perm_count, 25)))
        sms         = int(rng.integers(0, 2))
        phone       = int(rng.integers(0, 2))
        dex_count   = int(rng.integers(1, 5))
        obfuscated  = int(rng.integers(0, 2))
        row = [
            perm_count,
            dangerous,
            round(dangerous / max(perm_count, 1), 3),
            sms,                                # has_sms_permissions
            phone,                              # has_phone_permissions
            int(rng.integers(0, 2)),
            1,                                  # has_storage_permissions
            int(rng.integers(0, 2)),            # has_admin_permissions
            1,
            round(float(rng.uniform(2.0, 3.5)), 3),
            int(rng.integers(10, 40)),          # activity_count
            int(rng.integers(2, 8)),            # service_count
            int(rng.integers(2, 6)),            # receiver_count
            int(rng.integers(0, 3)),
            int(rng.integers(15, 55)),          # component_count
            int(rng.integers(2, 8)),            # exported_activity_count
            int(rng.integers(1, 4)),            # exported_service_count
            int(rng.integers(1, 4)),            # exported_receiver_count
            int(rng.integers(1, 4)),            # suspicious_receiver_count
            int(rng.integers(3, 12)),
            dex_count,
            int(rng.integers(0, 2)),            # has_reflection_api
            int(rng.integers(0, 2)),            # has_dynamic_code_loading
            1,                                  # has_crypto_api
            int(rng.integers(0, 2)),            # has_runtime_exec
            int(rng.integers(0, 2)),            # has_native_code_loading
            int(rng.integers(1, 6)),            # suspicious_api_count
            int(rng.integers(1, 4)),            # api_diversity_score
            int(rng.integers(0, 2)),            # cert_is_debug
            int(rng.integers(0, 2)),            # cert_is_valid
            round(float(rng.uniform(0.0, 1.0)), 3),
            int(rng.integers(0, 2)),            # cert_self_signed
            round(float(rng.uniform(0.2, 1.0)), 3),
            1,                                  # has_native_libs
            int(rng.integers(1, 5)),
            obfuscated,
            int(rng.integers(0, 3)),            # manifest_anomaly_count
            int(rng.integers(0, 5)),            # suspicious_string_count
            int(rng.integers(0, 2)),            # has_url_strings
            int(rng.integers(0, 2)),            # has_ip_strings
            1,                                  # has_dangerous_permissions (legacy)
            round(float(rng.uniform(0.2, 1.0)), 3),
            dex_count,
            1,
        ]
        rows.append(row + [1])  # label = 1 (malicious)

    cols = feature_names + ['label']
    assert len(rows[0]) == len(cols), \
        f"Row length {len(rows[0])} != columns {len(cols)}"
    return pd.DataFrame(rows, columns=cols)


def train_and_evaluate(X_train, X_test, y_train, y_test):
    models = {
        'Logistic Regression': Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(max_iter=1000, random_state=42,
                                       class_weight='balanced')),
        ]),
        'Random Forest': RandomForestClassifier(
            n_estimators=200, max_depth=12, random_state=42,
            class_weight='balanced',
        ),
    }

    best_model, best_score, best_name = None, 0.0, ''
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        acc  = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec  = recall_score(y_test, y_pred, zero_division=0)
        f1   = f1_score(y_test, y_pred, zero_division=0)

        print(f"\n{name}:")
        print(f"  Accuracy:  {acc:.4f}  Precision: {prec:.4f}"
              f"  Recall: {rec:.4f}  F1: {f1:.4f}")

        if f1 > best_score:
            best_score, best_model, best_name = f1, model, name

    print(f"\nBest model: {best_name}  (F1={best_score:.4f})")
    print(classification_report(y_test, best_model.predict(X_test),
                                 target_names=['Safe', 'Malicious']))
    return best_model, best_name


def main():
    print("=" * 60)
    print("SecureVision — APK Malware Model Training (44 features)")
    print("=" * 60)

    Config.MODELS_DIR.mkdir(exist_ok=True)

    # Load existing CSV (legacy 10-column) if available, else generate
    csv_path = Config.APK_DATA_PATH
    try:
        df_csv = pd.read_csv(csv_path)
        if len(df_csv.columns) < 44:
            print(f"CSV has {len(df_csv.columns)-1} features — generating synthetic 44-feature data")
            df = generate_synthetic_apk_data()
        else:
            df = df_csv
    except Exception:
        df = generate_synthetic_apk_data()

    print(f"Dataset: {len(df)} samples  "
          f"(safe={len(df[df.label==0])}, malicious={len(df[df.label==1])})")

    X = df.drop('label', axis=1).values
    y = df['label'].values

    print(f"Feature count: {X.shape[1]}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )

    best_model, best_name = train_and_evaluate(X_train, X_test, y_train, y_test)

    # Save
    joblib.dump(best_model, Config.APK_MODEL_PATH)
    print(f"\nSaved → {Config.APK_MODEL_PATH}")

    # Save feature names
    extractor = APKFeatureExtractor()
    feat_path = Config.MODELS_DIR / 'apk_feature_names.txt'
    feat_path.write_text('\n'.join(extractor.get_feature_names()))
    print(f"Saved feature names → {feat_path}")

    print("=" * 60)
    print("APK model training complete")
    print("=" * 60)


if __name__ == '__main__':
    main()
