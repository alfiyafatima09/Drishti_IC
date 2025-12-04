/**
 * Application configuration
 * Reads from environment variables
 */

// Backend URL - defaults to localhost:8000 for development
export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

// WebSocket URL - derived from backend URL
export const getWsUrl = (): string => {
  const url = new URL(BACKEND_URL);
  const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${url.host}`;
};

// API base URL
export const API_BASE = `${BACKEND_URL}/api/v1`;

export const config = {
  backendUrl: BACKEND_URL,
  wsUrl: getWsUrl(),
  apiBase: API_BASE,
} as const;

