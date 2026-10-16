# Implementation Plan — Stage 1: Landing Page + /dashboard Route

## Context summary
- **Framer Motion v11** is installed — use `motion.*` animations.
- Logo lives at `client/src/assets/logo.svg` (imported as module, not `/logo.svg` from public).
- Design tokens are in `tailwind.config.ts`: surfaces, accents, sev colors, content hierarchy.
- `api.scanUrl` in `client/src/api/client.ts` posts to `/api/scan/url` and returns `ScanResult`.
- Current routes: all pages are children of `<Layout>`, with `index` → `<Dashboard>`.
- Flask `/` returns `render_template('dashboard.html')` — leave it untouched. No Flask changes needed; the Vite dev server and React Router own all user-facing navigation.
- `framer-motion` animations: fade-in on hero (`initial opacity:0` → `animate opacity:1`), staggered container + child variants on feature cards.

---

- [ ] 1. Create `client/src/context/AuthContext.tsx` — skeleton AuthProvider and useAuth hook.
      Returns `{ user: null, loading: false }` always (Stage 2 will replace this). Export `AuthProvider` (wraps children with a context value) and `useAuth()`. Keep the type narrow: `User = null` for now.
      Files: `client/src/context/AuthContext.tsx`
      Verify: `cd client && npx tsc --noEmit` — no new errors.

- [ ] 2. Create `client/src/pages/Login.tsx` — Stage 2 placeholder page.
      Full-page dark surface layout (no sidebar). Shows SecureVision logo, heading "Sign In", and a grey notice box: "Authentication coming in Stage 2. Continue as guest →" (link to /dashboard). No broken imports.
      Files: `client/src/pages/Login.tsx`
      Verify: `npx tsc --noEmit` — passes.

- [ ] 3. Create `client/src/pages/Landing.tsx` — full public landing page with 7 sections.
      Import logo from `../../assets/logo.svg` (same pattern as Sidebar.tsx). Use `framer-motion` for hero fade-in and staggered feature cards. Use `useMutation` from `@tanstack/react-query` and `api.scanUrl` for the quick-scan strip. No fake statistics. All sections and IDs listed below; full TypeScript, no `any`. Full accessibility: h1 in hero, h2 on each section, aria-labels on icon-only buttons.

      Sections in order:
      a. **Sticky nav** — logo + "SecureVision" text, nav links scroll to `#features` and `#how-it-works` (use smooth `scrollIntoView`), "Open App" button → `/dashboard`, "Sign in" link → `/login`. Mobile hamburger toggle (useState). `sticky top-0 z-50 backdrop-blur-md bg-surface-raised/80 border-b border-surface-border`.
      b. **Hero** — `<h1>` "Detect threats before they reach you", sub-text, primary CTA (`btn-primary`) → `/dashboard`, secondary CTA (`btn-ghost`) → `/scan/url`. `motion.div` fade-in (`initial:{opacity:0,y:20}` → `animate:{opacity:1,y:0}` duration 0.6s).
      c. **Quick-scan strip** — label "Instant URL check — no account needed". `<input>` + "Scan" button. Calls `api.scanUrl(url)` via `useMutation`. States: idle (placeholder text), loading (spinner), result (verdict chip: green "SAFE" or red "PHISHING/MALICIOUS", confidence %), error (error message string). Show `<form onSubmit>` to support Enter key.
      d. **Feature cards** `id="features"` — 6 cards in CSS grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`). Use `motion` stagger container + `motion.div` children (`variants` approach, staggerChildren 0.08s). Cards: URL Scanner, Live Scan, Message & Email Scanner, APK Static Analysis, Explainable Results, Scan History & Insights. Each card: inline SVG icon (shield/link/wifi/package/lightbulb/clock using same SVG approach as Sidebar.tsx), `<h3>` title, 1-line description. `card` class.
      e. **How it works** `id="how-it-works"` — `<h2>`, horizontal strip (flex wrap on mobile). 4 steps: "Submit" / "Extract Features" / "ML + Rules" / "Explanation & Recommendations". Each: numbered circle (1-4, `bg-accent`), step title, 1-line description. Arrows between steps (hidden on mobile).
      f. **Privacy & Safety** — `<h2>`, 3 bullet points with lock SVG icon: "APKs are never executed — static analysis only", "URLs are not visited during Quick Scan — header and feature extraction only", "Email bodies are never stored — only verdicts and indicators are saved".
      g. **Footer** — `<footer>`, links: About (`href="#features"`), Models (`href="https://scikit-learn.org"`), GitHub (`href="https://github.com/mayur968/SecureVision-Intelligent-Cybersecurity-Threat-Detection-and-Analysis-System"`). Copyright line.

      Files: `client/src/pages/Landing.tsx`
      Verify: `npx tsc --noEmit` — passes.

- [ ] 4. Update `client/src/main.tsx` — restructure routes.
      - Wrap everything in `<AuthProvider>` (from `./context/AuthContext.js`).
      - Outside `<Layout>`: route `"/"` → `<Landing>`, route `"/login"` → `<Login>`.
      - Inside `<Layout>`: route `"dashboard"` → `<Dashboard>` (was the index route), plus `"scan/url"`, `"scan/message"`, `"scan/apk"`, `"history"` unchanged.
      - Catch-all `"*"` → `<Navigate to="/" replace />` (was pointing to "/" before, still correct).
      - Add a `<Route path="dashboard-legacy" element={<Navigate to="/dashboard" replace />}` inside Layout for the Flask alias hint (harmless, covers the case).
      - Import `Landing` from `./pages/Landing.js`, `Login` from `./pages/Login.js`, `AuthProvider` from `./context/AuthContext.js`.

      Files: `client/src/main.tsx`
      Verify: `npx tsc --noEmit` — passes.

- [ ] 5. Update `client/vite.config.ts` — add `/auth` proxy target.
      Add a second proxy entry: `'/auth': { target: 'http://localhost:5000', changeOrigin: true, secure: false }`. Keep the existing `/api` proxy entry untouched.
      Files: `client/vite.config.ts`
      Verify: `npx tsc --noEmit` — passes (vite config is in tsconfig.node.json scope, so just confirm no syntax errors).

- [ ] 6. Update `client/src/components/layout/Sidebar.tsx` — fix Dashboard nav link.
      Change the Dashboard nav item's `to` from `'/'` to `'/dashboard'` and set `end` to `true`. This ensures the sidebar correctly highlights Dashboard when the user is at `/dashboard` (not at the landing page `/`).
      Files: `client/src/components/layout/Sidebar.tsx`
      Verify: `npx tsc --noEmit` — passes.

- [ ] 7. Run TypeScript check and record output.
      From `client/`, run `npx tsc --noEmit`. All errors must be zero. If errors exist, fix them before continuing.
      Files: (none — verification step)
      Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` exits with code 0.

- [ ] 8. Run Playwright smoke tests and take screenshot.
      Use Playwright (already installed as devDependency). Assumes Vite dev server is running on :5173 and Flask on :5000.
      Tests:
      a. Navigate to `http://localhost:5173/` — assert `h1` contains "Detect threats", assert no `console.error` calls.
      b. Quick scan: fill URL input with `https://www.google.com`, click Scan, wait for verdict chip (text "SAFE" or "PHISHING"), assert it appears within 15s.
      c. Click "Open Dashboard" CTA — assert URL is now `/dashboard`.
      d. Navigate to `http://localhost:5173/dashboard` — assert page title area contains "Dashboard".
      e. Navigate to `http://localhost:5173/login` — assert page loads (no 404).
      Screenshot of landing page to `c:\Users\Mayur\Documents\SecureVision\.agents\tasks\stage1_landing.png`.
      Files: (test script only — clean up after run)
      Verify: All 5 assertions pass.

- [ ] 9. Write stage summary.
      Write a markdown file at `c:\Users\Mayur\Documents\SecureVision\.agents\tasks\stage1_complete.md` containing: what was built, file list, tsc output (pass/fail), Playwright results (pass counts), any deviations from spec.
      Files: `c:\Users\Mayur\Documents\SecureVision\.agents\tasks\stage1_complete.md`
      Verify: File exists and is non-empty.

- [ ] 10. Git commit.
       Stage and commit all changed/created files with message `"feat: Stage 1 — landing page, /dashboard route"`.
       Files: `client/src/context/AuthContext.tsx`, `client/src/pages/Landing.tsx`, `client/src/pages/Login.tsx`, `client/src/main.tsx`, `client/vite.config.ts`, `client/src/components/layout/Sidebar.tsx`
       Verify: `git log --oneline -1` shows the commit message.
