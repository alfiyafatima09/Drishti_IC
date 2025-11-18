const isBrowser = typeof window !== 'undefined';

const normalizeBase = (value?: string | null) => {
  if (!value) {
    return '';
  }
  return value.endsWith('/') ? value.slice(0, -1) : value;
};

const ENV_API_BASE = normalizeBase(process.env.NEXT_PUBLIC_API_URL || null);
const ENV_WS_BASE = normalizeBase(process.env.NEXT_PUBLIC_WS_URL || null);

export const API_BASE_URL =
  ENV_API_BASE || (isBrowser ? '' : 'http://localhost:8000');

export const WS_BASE_URL =
  ENV_WS_BASE ||
  (isBrowser
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${
        window.location.host
      }`
    : 'ws://localhost:8000');

const buildUrl = (base: string, path: string) => {
  const normalizedBase = normalizeBase(base);
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
};

export const API_ENDPOINTS = {
  // Health
  health: buildUrl(API_BASE_URL, '/api/v1/health'),
  healthDetailed: buildUrl(API_BASE_URL, '/api/v1/health/detailed'),

  // Verification
  verifyIC: buildUrl(API_BASE_URL, '/api/v1/verify/ic'),
  verificationResult: (id: number) =>
    buildUrl(API_BASE_URL, `/api/v1/verify/results/${id}`),
  verificationHistory: buildUrl(API_BASE_URL, '/api/v1/verify/history'),
  manufacturers: buildUrl(API_BASE_URL, '/api/v1/verify/manufacturers'),

  // Video
  videoSessionStart: buildUrl(API_BASE_URL, '/api/v1/video/sessions/start'),
  videoSessionActive: buildUrl(API_BASE_URL, '/api/v1/video/sessions/active'),
  videoSessionStatus: (id: string) =>
    buildUrl(API_BASE_URL, `/api/v1/video/sessions/${id}/status`),
  videoSessionStream: (id: string) =>
    buildUrl(API_BASE_URL, `/api/v1/video/sessions/${id}/stream`),

  // Images
  imageUpload: buildUrl(API_BASE_URL, '/api/v1/images/upload'),
  imageAnalyze: (id: string) =>
    buildUrl(API_BASE_URL, `/api/v1/images/${id}/analyze`),

  // Datasheets
  datasheetFetch: (partNumber: string) =>
    buildUrl(API_BASE_URL, `/api/v1/datasheets/fetch/${partNumber}`),
};
