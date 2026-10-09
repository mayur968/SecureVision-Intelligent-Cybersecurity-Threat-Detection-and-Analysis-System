# Playwright E2E Test Output — History Page

**Command:**
```
c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -m pytest tests/test_history_playwright.py -v --browser chromium
```

**Result:** ✅ ALL PASSED

```
===================================== test session starts =====================================
platform win32 -- Python 3.10.11, pytest-7.4.3, pluggy-1.6.0 -- C:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Mayur\Documents\SecureVision
configfile: pytest.ini
plugins: anyio-4.15.1, flask-1.3.0, playwright-0.10.0
collecting ... collected 6 items

tests/test_history_playwright.py::test_history_page_loads_no_console_errors[chromium0] PASSED [ 16%]
tests/test_history_playwright.py::test_history_legacy_row_shows_legacy_label[chromium0] PASSED [ 33%]
tests/test_history_playwright.py::test_history_filters_work[chromium0] PASSED            [ 50%]
tests/test_history_playwright.py::test_history_page_loads_no_console_errors[chromium1] PASSED [ 66%]
tests/test_history_playwright.py::test_history_legacy_row_shows_legacy_label[chromium1] PASSED [ 83%]
tests/test_history_playwright.py::test_history_filters_work[chromium1] PASSED            [100%]

===================================== 6 passed in 17.51s ======================================
```

## Test Descriptions

| Test | Status | Description |
|------|--------|-------------|
| `test_history_page_loads_no_console_errors` | ✅ PASSED | History page loads, table renders rows, no JS errors, no failed API requests |
| `test_history_legacy_row_shows_legacy_label` | ✅ PASSED | Rows with null model_version show 'legacy' chip in the Model column |
| `test_history_filters_work` | ✅ PASSED | URL type filter correctly narrows the table rows |

*Tests ran against Flask on :5000 and Vite on :5173.*
