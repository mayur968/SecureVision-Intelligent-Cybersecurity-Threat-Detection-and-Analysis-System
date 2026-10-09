export type RiskLevel  = 'LOW' | 'MEDIUM' | 'HIGH';
export type Prediction = 'SAFE' | 'PHISHING' | 'MALICIOUS' | 'UNKNOWN' | 'ERROR';
export type ScanType   = 'URL' | 'MESSAGE' | 'APK';

export interface ScanResult {
  success:         boolean;
  prediction:      Prediction;
  confidence:      number;
  risk_score:      number;
  risk_level:      RiskLevel;
  explanation:     string;
  recommendations: string[];
  indicators?:     string[];
  features?:       Record<string, unknown>;
  analysis_note?:  string;
  filename?:       string;
  file_size?:      number;
  error?:          string;
}

export interface HistoryScan {
  id:             number;
  scan_type:      ScanTypeExtended;
  input_value:    string;
  prediction:     Prediction;
  confidence:     number;
  risk_level:     RiskLevel;
  explanation:    string | null;
  recommendation: string | null;
  created_at:     string;
  // Phase 1 additions (nullable for legacy rows)
  risk_score:     number | null;
  duration_ms:    number | null;
  status:         string | null;
  model_version:  string | null;   // null legacy rows show as "legacy" in UI
  is_demo_data:   boolean | null;
  ioc_count:      number | null;
}

export interface Statistics {
  total_scans:      number;
  apk_scans:        number;
  url_scans:        number;
  message_scans:    number;
  threats_detected: number;
  safe_results:     number;
  threat_breakdown: { apk: number; url: number; message: number };
}

export type LiveScanVerdict = 'PHISHING' | 'SUSPICIOUS' | 'LIKELY_SAFE' | 'COULD_NOT_VERIFY';
export type ScanTypeExtended = ScanType | 'URL_LIVE';

export interface LiveScanResult {
  verdict: LiveScanVerdict;
  live_score: number;
  combined_score: number;
  final_url: string;
  redirect_chain: string[];
  title: string;
  evidence: string[];
  screenshot_b64: string | null;
  load_time_ms: number;
  ml_fallback?: boolean;
  prediction: string;
  confidence: number;
  risk_score: number;
  risk_level: string;
  explanation: string;
  recommendations: string[];
}

export interface LiveJobResponse {
  status: 'queued' | 'running' | 'done' | 'failed';
  result?: LiveScanResult;
  error?: string;
}
