import axios from 'axios';
import type { ScanResult, HistoryScan, Statistics, LiveJobResponse, EmailScanResult } from '../types/index.js';

const http = axios.create({ baseURL: '/api', timeout: 60_000 });

export const api = {
  scanUrl:     (url: string)             => http.post<ScanResult>('/scan/url',     { url }).then(r => r.data),
  scanMessage: (message: string)         => http.post<ScanResult>('/scan/message', { message }).then(r => r.data),
  scanApk:     (file: File, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append('file', file);
    return http.post<ScanResult>('/scan/apk', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
      onUploadProgress: e => onProgress?.(Math.round((e.loaded / (e.total ?? 1)) * 100)),
    }).then(r => r.data);
  },
  getHistory:    (limit = 50)  => http.get<{ success: boolean; count: number; scans: HistoryScan[] }>(`/history?limit=${limit}`).then(r => r.data),
  getStatistics: ()             => http.get<{ success: boolean; statistics: Statistics }>('/statistics').then(r => r.data),
  startLiveScan: (url: string) =>
    http.post<{ job_id: string; status: string }>('/scan/url/live', { url }).then(r => r.data),
  getLiveScanJob: (jobId: string) =>
    http.get<LiveJobResponse>(`/scan/url/live/${jobId}`).then(r => r.data),
  scanEmail: (file: File, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append('file', file);
    return http.post<EmailScanResult>('/scan/email/upload', fd, {
      headers:  { 'Content-Type': 'multipart/form-data' },
      timeout:  60_000,
      onUploadProgress: e => onProgress?.(Math.round((e.loaded / (e.total ?? 1)) * 100)),
    }).then(r => r.data);
  },
};
