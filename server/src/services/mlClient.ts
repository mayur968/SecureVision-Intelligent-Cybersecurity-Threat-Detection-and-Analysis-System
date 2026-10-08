/**
 * mlClient — thin typed wrapper around the Python ML microservice.
 * All HTTP calls go through here; the rest of the server never calls axios directly.
 */
import axios, { AxiosInstance } from 'axios';
import FormData from 'form-data';
import type { ScanResult, HistoryScan, Statistics, MLHealthResponse, LiveScanResult, LiveJobResponse, StartLiveScanResponse } from '../types/index.js';

const ML_BASE = process.env.ML_SERVICE_URL ?? 'http://localhost:5000';
const TIMEOUT = parseInt(process.env.ML_TIMEOUT_MS ?? '30000', 10);

const http: AxiosInstance = axios.create({
  baseURL: ML_BASE,
  timeout: TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
});

// ── Health ────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<MLHealthResponse> {
  const { data } = await http.get<MLHealthResponse>('/api/health');
  return data;
}

// ── Scans ─────────────────────────────────────────────────────────────────────

export async function scanUrl(url: string): Promise<ScanResult> {
  const { data } = await http.post<ScanResult>('/api/scan/url', { url });
  return data;
}

export async function scanMessage(message: string): Promise<ScanResult> {
  const { data } = await http.post<ScanResult>('/api/scan/message', { message });
  return data;
}

export async function scanApk(
  fileBuffer: Buffer,
  originalName: string,
  mimeType: string,
): Promise<ScanResult> {
  const form = new FormData();
  form.append('file', fileBuffer, { filename: originalName, contentType: mimeType });

  const { data } = await http.post<ScanResult>('/api/scan/apk', form, {
    headers: form.getHeaders(),
    timeout: 120_000,          // APK analysis can be slow
  });
  return data;
}

// ── History & statistics ───────────────────────────────────────────────────────

export async function getHistory(limit: number): Promise<{ count: number; scans: HistoryScan[] }> {
  const { data } = await http.get<{ success: boolean; count: number; scans: HistoryScan[] }>(
    '/api/history',
    { params: { limit } },
  );
  return { count: data.count, scans: data.scans };
}

export async function getStatistics(): Promise<Statistics> {
  const { data } = await http.get<{ success: boolean; statistics: Statistics }>('/api/statistics');
  return data.statistics;
}

// ── Live scan ──────────────────────────────────────────────────────────────────

export async function startLiveScan(url: string): Promise<StartLiveScanResponse> {
  const res = await http.post<StartLiveScanResponse>('/api/scan/url/live', { url });
  return res.data;
}

export async function getLiveScanJob(jobId: string): Promise<LiveJobResponse> {
  const res = await http.get<LiveJobResponse>(`/api/scan/url/live/${jobId}`);
  return res.data;
}
