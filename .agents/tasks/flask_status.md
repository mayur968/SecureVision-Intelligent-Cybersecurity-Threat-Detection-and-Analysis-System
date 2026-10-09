# Flask Startup Status — Step 4

## 4A. app.py change
`app.run(...)` updated to include `use_reloader=False` — prevents double-start and Windows `stat()` errors.

---

## 4B. Package install results

| Package | Status |
|---|---|
| tldextract | Already installed (5.4.0) |
| python-whois | Already installed (0.9.6) |
| Levenshtein | Already installed (0.27.4) |
| androguard | Already installed (4.1.0) |
| pytest-playwright | **Newly installed (0.10.0)** |
| python-slugify | Newly installed as dependency of pytest-playwright (9.1.3) |
| text-unidecode | Newly installed as dependency of python-slugify (1.3) |

---

## 4C. Playwright Chromium install

Playwright import verified successfully:
```
playwright ok
```
`python -m playwright install chromium` completed with exit code 0.

---

## 4D. Process on port 5000

- Found existing process PID 15768 (elevated/system context, not visible to tasklist) holding port 5000.
- Killed SecureVision venv python processes (PIDs 24920, 24968).
- New Flask process started via venv python — PID 15012 now listening on port 5000.
- Old PID 15768 connections in FinWait2 (winding down).

---

## 4E. Flask startup log (first 30 lines)

```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
         Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.249.174.206:5000
Press CTRL+C to quit
```

---

## Summary

| Check | Result |
|---|---|
| "WARNING - X not available" lines | **None** |
| use_reloader errors | **None** |
| stat() errors | **None** |
| Flask serving on port 5000 | ✅ Yes — PID 15012, State: Listen |
| Health check HTTP 200 | ✅ `{"service": "securevision-ml", "status": "ok"}` |
| use_reloader=False applied | ✅ Yes |
