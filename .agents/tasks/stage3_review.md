# .eml Email Scanner (Stage 3)

This stage adds a full-pipeline `.eml` scanner: a Python parser that extracts headers, auth results, links, and attachments; a Flask upload endpoint; a React drop-zone page wired into the existing sidebar and router; and 12 pytest tests. The core heuristic blends a message-detector base score with per-signal penalties (display-name spoofing, reply-to divergence, SPF/DKIM/DMARC failure, risky attachments, phishing links) capped at 100. A prior review pass addressed a 50 MB buffer-before-gate bug and a narrow `Prediction` type; both fixes are confirmed in this build.

**Watch for:**
- **Content-Length bypass (likely):** the early `content_length` guard fires only when the `Content-Length` header is present; a request without it skips straight to `f.read(5 MB + 1)`. The backstop read-cap catches it, but a multi-GB streaming request will still allocate up to 5 MB + 1 byte in-process before being rejected.
- **IOC extraction omitted (confirmed):** the email upload route constructs `ScanHistory` directly and never calls `extract_iocs`, so `ioc_count` is always 0 in the history API for email scans.
- **No rate limiting (confirmed):** the endpoint comment documents this as intentional parity with other scan routes, but unlike APK or URL scanning, email analysis runs two ML models (message + per-link URL detector) per request.

**Verdict**: APPROVED

---

## High-level view

The scanner's risk formula is fully implemented as specified: base score from the message detector, +15 for display-name mismatch, +15 for reply-to mismatch, +10 each for SPF/DKIM/DMARC failure, +10 per risky attachment (capped at +30), +5 per phishing link (capped at +20), clamped to [0, 100]. All 7 required risky extensions are present in `_RISKY_EXTENSIONS`, plus 5 extras (.bat, .cmd, .ps1, .vbs, .jar) that add conservative coverage. The thresholds (60 → HIGH/PHISHING, 30–59 → MEDIUM/SUSPICIOUS) match the spec.

`body_preview` is hardcoded `None` in the return dict and confirmed never populated. The indicators list comes from the message detector's category labels (strings like "Financial/monetary keywords"), not raw body excerpts — verified both by code inspection and a live check.

The upload route applies two size gates: a `content_length` header check (skippable by omitting the header) and a `read(5 MB + 1)` cap that cannot be bypassed. The combination is sound against honest clients; an adversary who omits the header still gets rejected but forces the server to buffer up to 5 MB + 1 byte first.

The email route saves to `ScanHistory` directly rather than via `save_scan()`, which means `extract_iocs` is never called and `ioc_count` is always 0 for email rows in the history view. The explanation field is populated from the first three evidence strings, which is a reasonable truncation.

The TypeScript side is clean: all five new interfaces are exported from `types/index.ts`, `EmailScanResult.body_preview` is typed `null` (not `string | null`), `EmailScanResult.prediction` uses the `Prediction` union which now includes `'SUSPICIOUS'`, and the `Statistics` interface carries `email_scans`. No existing exported types were removed or narrowed.

The drop zone carries `role="button"`, `tabIndex={0}`, and `onKeyDown` handling for Enter and Space — sufficient for keyboard navigation. URLs from the email body are rendered as truncated plain text in a table, never as anchor elements or via `dangerouslySetInnerHTML`, so there is no HTML injection surface in the results view.

---

<details>
<summary>Issues (2)</summary>

1. **IOC extraction omitted for email scans** — The email route constructs `ScanHistory` directly and skips `extract_iocs`, so `ioc_count` is permanently 0 for all email rows in the history API. Add an `ioc_list` population step or pass an empty list explicitly to `save_scan()` to make the omission intentional and auditable.

2. **Content-Length bypass allows full-buffer allocation** — When a client omits the `Content-Length` header, `request.content_length` is `None`, the early gate is skipped, and the server allocates up to 5 MB + 1 bytes before rejecting. Consider using Flask's `MAX_CONTENT_LENGTH` config or wrapping the file stream with a size-limited reader to enforce the cap at the WSGI layer rather than after buffering.

</details>

---

<details>
<summary>Details</summary>

### IOC extraction omitted for email scans

The APK, URL, and message routes all call `extract_iocs(scan_type, input, result)` and pass the result to `save_scan()`, which populates the `iocs` relationship. The email route bypasses `save_scan()` entirely and constructs `ScanHistory(...)` directly — `extract_iocs` is never called. As a result, `to_dict()` returns `ioc_count: 0` for every email scan. The history table will show 0 IOCs even for a scan that found phishing links and risky attachments. This is a confirmed gap rather than a blocking defect (the scan result itself is correct), but it breaks consistency with the other scan types.

### Content-Length bypass and buffer allocation

The double-gate pattern is:
```
if content_length is not None and content_length > 5 MB:   # skipped if header absent
    return 413
data = f.read(5 MB + 1)
if len(data) > 5 MB:                                       # always fires
    return 413
```

When the header is absent (`content_length is None`), the server always allocates up to 5 MB + 1 bytes before rejection. For a local threat platform this is low severity, but it is a measurable amplification surface if the service is ever exposed publicly. Setting `app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024` would enforce the cap at the Werkzeug/WSGI layer and eliminate the allocation window.

### Display-name mismatch false-positive boundary

`display_name_mismatch` uses `not any(w in from_domain for w in brand_in_display)` — a substring check against the full domain string. A sender like `"PayPal Support" <noreply@paypal-secure.com>` would *not* be flagged because `paypal` is a substring of `paypal-secure.com`. This is the correct conservative direction for a detector (reduces false positives) but means lookalike domains with the brand name embedded pass silently.

`reply_to_mismatch` flags any case where the reply-to domain differs from the from-domain, including legitimate mailing list setups. This is a known false-positive source for bulk senders (newsletters, CRMs), but it is the correct conservative choice for a phishing detector.

### Body exposure surface

`body_text` flows only into `message_detector.predict()` (truncated to 5,000 chars) and `_extract_hrefs`. It is never assigned to any return-dict key. The `indicators` list from the message detector is a list of category labels — confirmed by live inspection — so body text cannot leak through it. `test_body_not_in_response` recursively walks the full result dict against a sentinel string, making this a confirmed control.

### Test coverage

12 tests pass: 9 direct `scan_eml()` unit tests (header parsing, mismatch detection, auth result extraction, attachment risk classification, body non-exposure) plus 3 Flask endpoint tests (happy-path upload, non-`.eml` rejection, oversized-file rejection).

Not tested: multi-link emails with mixed phishing/safe URLs (verifies the +5-per-link cap and deduplication logic), emails with no `Authentication-Results` header (verifies `'unknown'` defaults don't contribute to risk), and the content-length bypass path (omitted `Content-Length` header with an oversized body).

### UI rendering and no raw-HTML surface

The drop zone carries `role="button"`, `tabIndex={0}`, and `onKeyDown` for Enter and Space. The hidden `<input type="file" accept=".eml" />` ref handles the file-picker path. Links are rendered as truncated plain text in a `<td>` — no anchor elements, no `dangerouslySetInnerHTML`. Sender display names flow through normal React interpolation and are escaped by the renderer; HTML in display names cannot execute.

</details>

---

<details>
<summary>File map</summary>

| File | Change |
|---|---|
| `detection/email_scanner.py` | New: .eml parser, risk scorer, body/link/attachment extractor |
| `app.py` | New: `scan_email_upload` route; patched `api_get_statistics` with `email_scans` |
| `client/src/types/index.ts` | New: `EmailSender`, `EmailAuthResults`, `EmailLink`, `EmailAttachment`, `EmailScanResult`; extended `ScanTypeExtended` and `Prediction` |
| `client/src/api/client.ts` | New: `scanEmail()` method |
| `client/src/pages/EmailScanner.tsx` | New: file drop zone, scan result renderer |
| `client/src/components/layout/Sidebar.tsx` | New: `Email` SVG icon, `scan/email` nav entry |
| `client/src/main.tsx` | New: `scan/email` route under Layout |
| `tests/test_email_scanner.py` | New: 12 tests (9 unit + 3 endpoint) |

Full diff: `git diff main` from project root.

</details>
