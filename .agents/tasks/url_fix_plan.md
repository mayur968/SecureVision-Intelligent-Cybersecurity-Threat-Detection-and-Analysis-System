# Implementation Plan — URL False-Positive Fix + Venv Launcher

## Confirmed root causes (from live exploration)

- `scripts/diagnose_models.py` shows the URL model was trained on **100 rows (50 safe / 50 phishing)**.
  The model reaches train-accuracy 1.0 and 61% of predictions come out at >99.9% or <0.1% confidence —
  a clear overfit on the tiny, keyword-heavy toy dataset.
- Live test on `https://accounts.google.com/signin?hl=en` returns `PHISHING 0.999` — confirmed.
- `_count_suspicious_keywords()` in `features/url_features.py` scans the **entire raw URL string**,
  so `accounts.google.com/signin` scores 3 keywords (account, secure, signin).
- `playwright` IS installed in the venv. The "No module named playwright" error occurs because users
  run `python app.py` with the system Python instead of the venv Python.
- The **running service** is `ml-service/app.py` (port 5000, consumed by Node gateway at 4000).
  Root `app.py` is the legacy Jinja2 UI — both share the same detectors/features code so both benefit
  from every fix made in this plan.

---

- [ ] 1. Harden `_count_suspicious_keywords()` in `features/url_features.py` to only count keywords
      that appear in the **domain** portion, and only if the domain is not a known brand.

      **Current behaviour:** `keyword in url_lower` — scans entire URL including path and query.
      **Fix:** Parse the netloc from the URL, extract the registrable domain (use `tldextract` when
      available, fall back to `parts[-2]` split-by-dot), then compare against the existing
      `POPULAR_BRANDS` list. If the registrable domain exactly matches a POPULAR_BRANDS entry
      (e.g. `google.com`), return 0. Otherwise count keywords found only in `netloc.lower()`
      (not path/query).

      ```python
      def _count_suspicious_keywords(self, url_lower: str) -> int:
          """Count suspicious keywords in the DOMAIN only, skip known brands."""
          try:
              from urllib.parse import urlparse
              parsed = urlparse(url_lower)
              netloc = parsed.netloc.split(':')[0]   # strip port

              # Extract registrable domain
              if self.tldextract_available:
                  ext = self.tldextract.extract(netloc)
                  reg_domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else netloc
              else:
                  parts = netloc.split('.')
                  reg_domain = '.'.join(parts[-2:]) if len(parts) >= 2 else netloc

              # If it's a known brand, never count keywords
              if reg_domain in [b.lower() for b in self.POPULAR_BRANDS]:
                  return 0

              # Count keywords in the domain only (not path/query)
              count = 0
              for keyword in self.SUSPICIOUS_KEYWORDS:
                  if keyword in netloc:
                      count += 1
              return count
          except Exception:
              return 0
      ```

      **Files:** `features/url_features.py`
      **Verify:** `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\pytest.exe tests/test_url_detector.py -v`
      All existing tests pass. Manually confirm:
      `venv\Scripts\python.exe -c "from features.url_features import URLFeatureExtractor; e=URLFeatureExtractor(skip_whois=True); print(e.extract_features('https://accounts.google.com/signin')['suspicious_keywords'])"` → prints `0`.
      And for `http://secure-login-verify.com` → prints `3` (or more).

---

- [ ] 2. Add a `TRUSTED_DOMAINS` whitelist to `detection/url_detector.py` and a guard at the top of
      `predict()` that short-circuits before the model runs.

      Add a module-level frozenset `TRUSTED_DOMAINS` containing at minimum these 50 registrable
      domains (add them exactly as shown — lowercase, no `www.`):

      ```
      google.com, youtube.com, facebook.com, instagram.com, twitter.com,
      linkedin.com, microsoft.com, apple.com, amazon.com, netflix.com,
      paypal.com, ebay.com, wikipedia.org, reddit.com, github.com,
      stackoverflow.com, dropbox.com, adobe.com, salesforce.com, ibm.com,
      oracle.com, yahoo.com, outlook.com, live.com, office.com,
      windows.com, bing.com, skype.com, xbox.com, azure.com,
      icloud.com, itunes.com, appstore.com, support.apple.com (registered: apple.com),
      bankofamerica.com, wellsfargo.com, chase.com, citibank.com,
      americanexpress.com, visa.com, mastercard.com,
      mozilla.org, w3.org, python.org, cloudflare.com,
      shopify.com, stripe.com, twilio.com, zoom.us, slack.com
      ```

      Note: the set stores only **registrable domains** (no subdomains), e.g. `google.com` covers
      `accounts.google.com`, `mail.google.com`, `login.google.com`, etc.

      In `predict()`, right after the URL is normalised (after `url_clean = normalize_url(url)`)
      and **before** feature extraction or model inference, add:

      ```python
      # ── Whitelist guard ──────────────────────────────────────────────
      reg_domain = self._get_registrable_domain(url_clean)
      if reg_domain and reg_domain in TRUSTED_DOMAINS:
          logger.info(f"Whitelisted domain: {reg_domain} — returning SAFE")
          return {
              'prediction':      'SAFE',
              'confidence':      0.99,
              'features':        {},
              'important_features': {},
              'model_available': True,
              'url_analyzed':    url_clean,
              'whitelisted':     True,
          }
      ```

      Add a private helper method `_get_registrable_domain(self, url: str) -> str` that uses
      `tldextract` (via `self.feature_extractor.tldextract` — reuse the already-imported instance)
      when available, otherwise falls back to `urlparse` + last two dot-parts.

      **Files:** `detection/url_detector.py`
      **Verify:**
      ```
      venv\Scripts\pytest.exe tests/test_url_detector.py -v
      ```
      All existing tests pass. Also run the manual spot-check script described in item 4.

---

- [ ] 3. Expand `data/urls/sample_urls.csv` from 100 to ~150 rows.

      Keep every existing row unchanged. Append the following new rows (copy exactly):

      **50 legitimate URLs containing keywords (label=0) — teaches the model keywords ≠ phishing:**
      ```
      https://accounts.google.com/signin,0
      https://mail.google.com/mail/u/0/,0
      https://myaccount.google.com/security,0
      https://login.microsoftonline.com,0
      https://account.microsoft.com,0
      https://login.live.com,0
      https://secure.microsoft.com,0
      https://support.microsoft.com,0
      https://www.paypal.com/signin,0
      https://www.paypal.com/myaccount/summary,0
      https://www.paypal.com/us/webapps/mpp/account-selection,0
      https://www.amazon.com/gp/css/homepage.html,0
      https://www.amazon.com/ap/signin,0
      https://www.amazon.com/gp/your-account/order-history,0
      https://secure.bankofamerica.com,0
      https://www.bankofamerica.com/online-banking/sign-in/,0
      https://online.wellsfargo.com/signon,0
      https://www.chase.com/digital/myAccounts/signIn,0
      https://citibank.com/signin,0
      https://support.apple.com/account/,0
      https://appleid.apple.com/sign-in,0
      https://support.apple.com,0
      https://www.ebay.com/signin,0
      https://login.yahoo.com,0
      https://login.yahoo.com/account/security,0
      https://account.live.com/password/reset,0
      https://login.dropbox.com,0
      https://www.instagram.com/accounts/login/,0
      https://www.facebook.com/login,0
      https://www.facebook.com/security/,0
      https://twitter.com/login,0
      https://linkedin.com/login,0
      https://github.com/login,0
      https://github.com/account/security,0
      https://secure.netflix.com/login,0
      https://www.netflix.com/account,0
      https://www.reddit.com/login,0
      https://stackoverflow.com/users/login,0
      https://www.adobe.com/account/sign-in.html,0
      https://account.adobe.com/security,0
      https://www.salesforce.com/form/signup/freetrial.jsp,0
      https://login.salesforce.com,0
      https://slack.com/signin,0
      https://app.slack.com/sign-in,0
      https://zoom.us/signin,0
      https://www.dropbox.com/account/security,0
      https://outlook.office.com/mail/,0
      https://login.windows.net,0
      https://myapps.microsoft.com,0
      https://portal.azure.com,0
      ```

      **30 realistic phishing URLs (label=1) — typosquatting, unusual TLDs, subdomain abuse:**
      ```
      http://amaz0n-account-verify.net/login,1
      http://paypal-suspended-account.tk/verify,1
      http://microsoft-security-alert.xyz/update,1
      http://google-account-disabled.ml/restore,1
      http://apple-id-locked-verify.ga/signin,1
      http://facebo0k-security-check.com/login,1
      http://netfl1x-billing-update.net/payment,1
      http://secure-paypa1.com/confirm-account,1
      http://amazon-prime-renew.xyz/billing,1
      http://account-google-suspended.tk/unlock,1
      http://verify.paypal-account-limited.com/secure,1
      http://login.microsofft.com/signin,1
      http://accounts.g00gle.com/verify,1
      http://secure.app1e.com/id/signin,1
      http://mail.gooogle.com/account/verify,1
      http://update.amaz0n-prime.com/account,1
      http://ebay-account-suspended.ml/verify,1
      http://chase-banking-alert.xyz/signin,1
      http://wellsfarg0-secure.net/banking,1
      http://irs-tax-refund-claim.ga/apply,1
      http://fedex-package-delivery-alert.com/track,1
      http://ups-package-suspended.net/reschedule,1
      http://dhl-delivery-failed.xyz/verify,1
      http://netflix-account-hold.ml/payment,1
      http://your-account-suspended-action-required.com/unlock,1
      http://security.paypal-update-required.net/login,1
      http://billing.netflix-payment-failed.com/update,1
      http://accounts.google-security-alert.xyz/verify,1
      http://login.microsoft-account-review.net/confirm,1
      http://secure.amazon-prime-suspended.com/renew,1
      ```

      **Files:** `data/urls/sample_urls.csv`
      **Verify:** Row count — run `venv\Scripts\python.exe -c "import pandas as pd; df=pd.read_csv('data/urls/sample_urls.csv'); print(len(df), df['label'].value_counts().to_dict())"` from the project root. Should print `180 {0: 100, 1: 80}` (100 safe, 80 phishing, 180 total).

---

- [ ] 4. Retrain the URL model with the expanded dataset.

      Run the training script with the venv Python from the project root:
      ```
      c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe training/train_url_model.py
      ```
      The script reads `Config.URL_DATA_PATH` (`data/urls/sample_urls.csv`), extracts 43 features
      from every row with `skip_whois=True`, trains both LogisticRegression and RandomForest,
      picks the best by F1, and saves to `models/url_model.pkl`.

      After training, write a quick verification script `scripts/verify_url_fix.py`:

      ```python
      """Verify the retrained URL model does not flag legitimate sites as phishing."""
      import sys
      from pathlib import Path
      sys.path.insert(0, str(Path(__file__).parent.parent))

      from detection.url_detector import URLDetector

      detector = URLDetector()

      SHOULD_BE_SAFE = [
          'https://www.google.com',
          'https://accounts.google.com/signin',
          'https://www.amazon.com',
          'https://www.amazon.com/gp/css/homepage.html',
          'https://login.microsoftonline.com',
          'https://secure.bankofamerica.com',
          'https://www.paypal.com/signin',
          'https://support.apple.com',
          'https://www.netflix.com/account',
          'https://github.com/login',
      ]

      SHOULD_BE_PHISHING = [
          'http://paypal-suspended-account.tk/verify',
          'http://amaz0n-account-verify.net/login',
          'http://microsoft-security-alert.xyz/update',
          'http://accounts.google-security-alert.xyz/verify',
          'http://secure-login-verify-account.com/signin',
          'http://192.168.1.100/login/verify',
      ]

      print("=== SAFE URLs (expect SAFE) ===")
      safe_pass = True
      for url in SHOULD_BE_SAFE:
          r = detector.predict(url)
          status = "OK" if r['prediction'] == 'SAFE' else "FAIL"
          if status == "FAIL":
              safe_pass = False
          print(f"  [{status}] {r['prediction']} ({r['confidence']:.3f})  {url}")

      print("\n=== PHISHING URLs (expect PHISHING) ===")
      phish_pass = True
      for url in SHOULD_BE_PHISHING:
          r = detector.predict(url)
          status = "OK" if r['prediction'] == 'PHISHING' else "FAIL"
          if status == "FAIL":
              phish_pass = False
          print(f"  [{status}] {r['prediction']} ({r['confidence']:.3f})  {url}")

      if safe_pass and phish_pass:
          print("\nAll checks passed!")
          sys.exit(0)
      else:
          print("\nSome checks FAILED — review model or whitelist.")
          sys.exit(1)
      ```

      **Files:** `models/url_model.pkl` (overwritten), `scripts/verify_url_fix.py` (new)
      **Verify:**
      ```
      c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe scripts/verify_url_fix.py
      ```
      Must print "All checks passed!" and exit 0.
      If the whitelist from item 2 is in place, the SAFE URLs will pass even if the model still
      mispredicts them (the whitelist fires first). The phishing URLs must be caught by the model.

---

- [ ] 5. Add a venv startup check to both `app.py` files.

      Insert the following block **at the top of both `app.py` and `ml-service/app.py`**, immediately
      after the module-level docstring and before any other imports:

      ```python
      import sys as _sys, os as _os
      def _check_venv():
          """Warn loudly if not running from the project venv."""
          venv_python = _os.path.join(
              _os.path.dirname(_os.path.abspath(__file__)), 'venv', 'Scripts', 'python.exe'
          )
          running = _sys.executable.replace('\\', '/')
          expected = venv_python.replace('\\', '/')
          if running.lower() != expected.lower():
              print(
                  "\n" + "="*70 + "\n"
                  "WARNING: You are NOT running from the project venv.\n"
                  f"  Running:  {_sys.executable}\n"
                  f"  Expected: {venv_python}\n"
                  "  Some packages (playwright, tldextract, androguard) may be missing.\n"
                  "  Run with:  .\\venv\\Scripts\\python.exe app.py\n"
                  "  Or use:    .\\run.bat  (Windows CMD)  /  .\\run.ps1  (PowerShell)\n"
                  + "="*70 + "\n",
                  file=_sys.stderr
              )
      _check_venv()
      del _check_venv, _sys, _os
      ```

      For `ml-service/app.py` the expected path uses `..` because the file is one level deeper —
      adjust to `os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'venv', ...)`.

      **Files:** `app.py`, `ml-service/app.py`
      **Verify:** Run `python app.py` (system Python, not venv) and confirm the WARNING block is
      printed to stderr. Run `venv\Scripts\python.exe app.py` and confirm no warning appears.
      (Interrupt with Ctrl+C immediately — just checking startup output.)

---

- [ ] 6. Create `run.bat`, `run.ps1`, `run_tests.bat`, and `run_tests.ps1` at the project root.

      **`run.bat`** — starts the full stack (requires npm):
      ```bat
      @echo off
      echo Starting SecureVision (venv + npm run dev)...
      call "%~dp0venv\Scripts\activate.bat"
      npm run dev
      ```

      **`run.ps1`** — PowerShell equivalent:
      ```powershell
      # Run from SecureVision root
      $root = Split-Path -Parent $MyInvocation.MyCommand.Path
      & "$root\venv\Scripts\Activate.ps1"
      npm run dev
      ```

      **`run_tests.bat`**:
      ```bat
      @echo off
      echo Running SecureVision tests with venv Python...
      call "%~dp0venv\Scripts\activate.bat"
      pytest tests\ -v %*
      ```

      **`run_tests.ps1`**:
      ```powershell
      $root = Split-Path -Parent $MyInvocation.MyCommand.Path
      & "$root\venv\Scripts\Activate.ps1"
      & "$root\venv\Scripts\pytest.exe" tests\ -v @args
      ```

      **Files:** `run.bat`, `run.ps1`, `run_tests.bat`, `run_tests.ps1` (all at project root)
      **Verify:** `.\run_tests.ps1` (or `run_tests.bat`) completes with all existing tests passing.

---

- [ ] 7. Update `README.md` — add a "Running the Application" callout emphasising the venv.

      Find the existing `### 2 — Start all three services` section and add this callout immediately
      before the `npm run dev` code block:

      ```markdown
      > **Important — always use the venv Python.**
      > Running `python app.py` or `pytest` with the system Python will fail because packages like
      > `playwright`, `tldextract`, and `androguard` are only installed in `venv/`.
      >
      > **Easiest way to start everything:**
      > ```powershell
      > .\run.ps1          # PowerShell
      > # or
      > run.bat            # Windows CMD
      > ```
      > To run tests:
      > ```powershell
      > .\run_tests.ps1    # PowerShell
      > # or
      > run_tests.bat      # Windows CMD
      > ```
      ```

      Also update the **Running Tests** section at the bottom — replace the bare `pytest tests/ -v`
      with:
      ```powershell
      .\run_tests.ps1
      # or manually:
      .\venv\Scripts\Activate.ps1
      pytest tests/ -v
      ```

      **Files:** `README.md`
      **Verify:** No code changes — visual review of the markdown diff.

---

- [ ] 8. Run the full test suite and confirm all tests pass.

      ```powershell
      c:\Users\Mayur\Documents\SecureVision\venv\Scripts\pytest.exe tests\ -v --ignore=tests/test_history_playwright.py --ignore=tests/test_live_scanner.py
      ```

      (Playwright end-to-end tests require the dev server running; skip them here. The unit tests for
      URL detector, phase1, message detector, and APK detector must all pass.)

      Expected: all tests in `test_url_detector.py`, `test_phase1.py`, `test_message_detector.py`,
      `test_apk_detector.py` pass with no failures.

      **Files:** none changed in this step
      **Verify:** pytest exit code 0; no FAILED lines in output.

---

## Dependency order

Items 1 and 2 are independent and can be done in parallel, but both must be done before item 3.
Item 4 (retrain) depends on items 1, 2, and 3 being done.
Items 5 and 6 are independent of everything else.
Item 7 depends on item 6 (references the new scripts).
Item 8 is the final verification gate; depends on all prior items.

## Notes for the implementer

- The **running service** consumed by the React/Node stack is `ml-service/app.py`. Root `app.py`
  is the legacy Jinja2 UI. Both import from the same `detection/`, `features/`, and `models/`
  directories, so any fix in those shared modules benefits both automatically. Only the venv check
  (item 5) requires edits to both app.py files directly.

- The `TRUSTED_DOMAINS` frozenset in `url_detector.py` is a **belt-and-suspenders** safety net for
  high-value brands that the model might still misclassify after retraining. It must never trigger
  on an actually-malicious URL because it checks the **registrable domain**, not the full URL — a
  phishing URL at `paypal-login.com` will not match `paypal.com`.

- Do not modify `pytest.ini` or `config.py`. Tests run with `TESTING=true` and use in-memory SQLite.

- After retraining, `models/url_model.pkl` is overwritten. This is intentional. The old model was
  overfit on 100 rows; the new 180-row dataset is still small but the whitelist + keyword-domain fix
  will prevent most false positives even if the model is imperfect.
