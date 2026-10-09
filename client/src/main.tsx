import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './index.css';

import Layout        from './components/layout/Layout.js';
import Dashboard     from './pages/Dashboard.js';
import UrlScanner    from './pages/UrlScanner.js';
import MessageScanner from './pages/MessageScanner.js';
import ApkScanner    from './pages/ApkScanner.js';
import History       from './pages/History.js';
import ErrorBoundary from './components/ui/ErrorBoundary.js';

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
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index              element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
            <Route path="scan/url"    element={<ErrorBoundary><UrlScanner /></ErrorBoundary>} />
            <Route path="scan/message" element={<ErrorBoundary><MessageScanner /></ErrorBoundary>} />
            <Route path="scan/apk"    element={<ErrorBoundary><ApkScanner /></ErrorBoundary>} />
            <Route path="history"     element={<ErrorBoundary><History /></ErrorBoundary>} />
            <Route path="*"           element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
