/**
 * Theme configuration and utilities
 */

export const themes = {
  light: {
    name: 'light',
    colors: {
      primary: '#3b82f6',
      secondary: '#64748b',
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      background: '#ffffff',
      foreground: '#0f172a',
    },
  },
  dark: {
    name: 'dark',
    colors: {
      primary: '#60a5fa',
      secondary: '#94a3b8',
      success: '#34d399',
      warning: '#fbbf24',
      error: '#f87171',
      background: '#0f172a',
      foreground: '#f8fafc',
    },
  },
} as const;

export type Theme = keyof typeof themes;

export function getTheme(theme: Theme) {
  return themes[theme];
}

