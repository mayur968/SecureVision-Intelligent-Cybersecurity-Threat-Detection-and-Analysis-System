import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './index.css';

import { AuthProvider }   from './context/AuthContext.js';
import Layout             from './components/layout/Layout.js';
import Landing            from './pages/Landing.js';
import Login              from './pages/Login.js';
import Dashboard          from './pages/Dashboard.js';
import UrlScanner         from './pages/UrlScanner.js';
import MessageScanner     from './pages/MessageScanner.js';
import ApkScanner         from './pages/ApkScanner.js';
import History            from './pages/History.js';
import ErrorBoundary      from './components/ui/ErrorBoundary.js';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime:  30_000,
      retry:      1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public full-page routes (no sidebar layout) */}
            <Route path="/"     element={<Landing />} />
            <Route path="/login" element={<Login />} />

            {/* App routes inside the sidebar Layout */}
            <Route element={<Layout />}>
              <Route path="dashboard"          element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
              <Route path="scan/url"           element={<ErrorBoundary><UrlScanner /></ErrorBoundary>} />
              <Route path="scan/message"       element={<ErrorBoundary><MessageScanner /></ErrorBoundary>} />
              <Route path="scan/apk"           element={<ErrorBoundary><ApkScanner /></ErrorBoundary>} />
              <Route path="history"            element={<ErrorBoundary><History /></ErrorBoundary>} />
              {/* Legacy redirect so old bookmarks still work */}
              <Route path="dashboard-legacy"   element={<Navigate to="/dashboard" replace />} />
            </Route>

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
