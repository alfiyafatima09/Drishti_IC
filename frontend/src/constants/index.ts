/**
 * Application-wide constants
 */

export const APP_NAME = 'Drishti IC Verification';
export const APP_DESCRIPTION = 'AI-powered IC authenticity verification system';

export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  SCANNER: '/scanner',
  MOBILE: '/mobile',
  HISTORY: '/history',
  RESULTS: (id: string) => `/results/${id}`,
} as const;

export const STORAGE_KEYS = {
  THEME: 'drishti-theme',
  USER_PREFERENCES: 'drishti-user-preferences',
} as const;

export const WEBSOCKET = {
  MAX_RECONNECT_ATTEMPTS: 5,
  RECONNECT_DELAY: 1000,
  CONNECTION_TIMEOUT: 10000,
} as const;

export const FILE_UPLOAD = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  ACCEPTED_TYPES: ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'],
  ACCEPTED_EXTENSIONS: ['.jpg', '.jpeg', '.png', '.webp'],
} as const;

export const VERIFICATION_STATUS = {
  GENUINE: 'genuine',
  COUNTERFEIT: 'counterfeit',
  SUSPICIOUS: 'suspicious',
  UNKNOWN: 'unknown',
} as const;

export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.9,
  MEDIUM: 0.7,
  LOW: 0.5,
} as const;

