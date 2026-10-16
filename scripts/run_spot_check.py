"""
Run the 30-URL spot check and print a result table.
Reports false positives and false negatives honestly.
No network calls are made.

Usage:
    venv\Scripts\python.exe scripts/run_spot_check.py
"""
import sys, pathlib, csv, os
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

os.environ['SKIP_VENV_CHECK'] = '1'
os.environ['TESTING'] = 'true'   # prevents app.py from trying to seed DB

from detection.url_detector import URLDetector
import tldextract as _tld_mod

# Build an offline TLDExtract — no PSL download, uses bundled snapshot
_offline_tld = _tld_mod.TLDExtract(suffix_list_urls=(), cache_dir=None)

detector = URLDetector()
detector.feature_extractor._skip_whois = True
detector.feature_extractor.whois_available = False
detector.feature_extractor.tldextract = _offline_tld
detector.feature_extractor.tldextract_available = True

CSV = pathlib.Path(__file__).parent.parent / 'tests' / 'spot_check_urls.csv'

rows = []
with open(CSV, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        rows.append(row)

correct = fp = fn = 0
results = []

for r in rows:
    url      = r['url']
    expected = r['expected_label']
    notes    = r['notes']

    res  = detector.predict(url)
    pred = res['prediction']
    src  = res.get('source', 'model')
    conf = res.get('confidence')
    conf_str = f"{conf*100:.0f}%" if conf is not None else "—"

    if pred == expected:
        verdict = 'CORRECT'
        correct += 1
    elif pred == 'PHISHING' and expected == 'SAFE':
        verdict = 'FALSE POSITIVE'
        fp += 1
    elif pred == 'SAFE' and expected == 'PHISHING':
        verdict = 'FALSE NEGATIVE'
        fn += 1
    else:
        verdict = f'WRONG ({pred})'

    results.append((url, expected, pred, conf_str, src, verdict, notes))

hdr = f"{'URL':<55} {'EXPECT':<10} {'GOT':<10} {'CONF':>6} {'SOURCE':<22} RESULT"
print(hdr)
print('-' * 120)
for url, expected, pred, conf_str, src, verdict, notes in results:
    u = url[:53] + '..' if len(url) > 55 else url
    flag = ' <<<' if 'POSITIVE' in verdict or 'NEGATIVE' in verdict else ''
    print(f"{u:<55} {expected:<10} {pred:<10} {conf_str:>6} {src:<22} {verdict}{flag}")

total = len(rows)
acc = correct / total * 100
print()
print(f"Results: {correct}/{total} correct ({acc:.0f}%)  "
      f"| False positives: {fp}  | False negatives: {fn}")
print()
if fp:
    print("FALSE POSITIVES (legitimate sites flagged as phishing):")
    for url, expected, pred, conf_str, src, verdict, notes in results:
        if verdict == 'FALSE POSITIVE':
            print(f"  {url}")
            print(f"    Reason: {notes}")
if fn:
    print("FALSE NEGATIVES (phishing URLs marked safe):")
    for url, expected, pred, conf_str, src, verdict, notes in results:
        if verdict == 'FALSE NEGATIVE':
            print(f"  {url}")
            print(f"    Reason: {notes}")
if not fp and not fn:
    print("No errors on this set.")
