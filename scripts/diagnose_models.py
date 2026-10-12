"""Model diagnostics — runs during audit, outputs to stdout."""
import joblib, numpy as np, pandas as pd, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

BASE = pathlib.Path(__file__).parent.parent

MODELS = {
    'url':     ('models/url_model.pkl',     'data/urls/sample_urls.csv'),
    'message': ('models/message_model.pkl', 'data/messages/sample_messages.csv'),
    'apk':     ('models/apk_model.pkl',     'data/apk/sample_apk_features.csv'),
}

print("=" * 70)
print("MODEL DIAGNOSTICS")
print("=" * 70)

for name, (mpth, dpth) in MODELS.items():
    print(f"\n--- {name.upper()} ---")
    m = joblib.load(BASE / mpth)
    clf = m.steps[-1][1] if hasattr(m, 'steps') else m
    alg = type(clf).__name__

    nf = getattr(clf, 'n_features_in_', '?')
    C  = getattr(clf, 'C', 'N/A')
    solver = getattr(clf, 'solver', 'N/A')
    max_iter = getattr(clf, 'max_iter', 'N/A')

    print(f"  Algorithm    : {alg}")
    print(f"  n_features   : {nf}")
    print(f"  C (reg.)     : {C}")
    print(f"  solver       : {solver}")
    print(f"  max_iter     : {max_iter}")

    try:
        coef = clf.coef_
        print(f"  coef shape   : {coef.shape}")
        print(f"  max |coef|   : {np.abs(coef).max():.4f}")
        print(f"  max intercept: {np.abs(clf.intercept_).max():.4f}")
    except Exception as e:
        print(f"  coef error   : {e}")

    # Load training data and evaluate
    try:
        df = pd.read_csv(BASE / dpth)
        print(f"  Dataset rows : {len(df)}")
        print(f"  Label dist   : {df['label'].value_counts().to_dict()}")

        if name == 'url':
            from features.url_features import URLFeatureExtractor
            ext = URLFeatureExtractor(skip_whois=True)
            X = np.array([list(ext.extract_features(u).values()) for u in df['url'].values])
            y = df['label'].values
        elif name == 'message':
            from preprocessing.text_preprocessing import TextPreprocessor
            prep = TextPreprocessor()
            vect = joblib.load(BASE / 'models/message_vectorizer.pkl')
            cleaned = [prep.preprocess(msg) for msg in df['message'].values]
            X = vect.transform(cleaned)
            y = df['label'].values
        elif name == 'apk':
            X = df.drop('label', axis=1).values
            y = df['label'].values

        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import cross_val_score

        if hasattr(m, 'predict'):
            y_pred = m.predict(X)
        else:
            y_pred = clf.predict(X)

        acc = accuracy_score(y, y_pred)
        f1  = f1_score(y, y_pred, zero_division=0)
        print(f"  Train acc    : {acc:.4f}  (resubstitution — OPTIMISTIC)")
        print(f"  Train F1     : {f1:.4f}  (resubstitution — OPTIMISTIC)")

        # Confidence distribution
        try:
            if hasattr(m, 'predict_proba'):
                proba = m.predict_proba(X)[:, 1]
            else:
                proba = clf.predict_proba(X)[:, 1]
            pct = np.percentile(proba, [0, 10, 50, 90, 99, 100])
            print(f"  Confidence p : min={pct[0]:.4f} p10={pct[1]:.4f} median={pct[2]:.4f} "
                  f"p90={pct[3]:.4f} p99={pct[4]:.4f} max={pct[5]:.4f}")
            # Count suspiciously extreme predictions
            extreme = np.sum((proba > 0.999) | (proba < 0.001))
            print(f"  Extreme conf : {extreme}/{len(proba)} ({extreme/len(proba)*100:.1f}%) "
                  f"predictions at >99.9% or <0.1%")
        except Exception as e:
            print(f"  Confidence   : {e}")

    except Exception as e:
        print(f"  Data eval error: {e}")

print("\n" + "=" * 70)
print("END DIAGNOSTICS")
print("=" * 70)
