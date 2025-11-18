/**
 * Formatting utility functions
 */

/**
 * Format a number as a percentage
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format a date string
 */
export function formatDate(date: string | Date, format: 'short' | 'long' = 'short'): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  if (format === 'long') {
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
  
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a file size in bytes to human-readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, length: number): string {
  if (text.length <= length) return text;
  return `${text.substring(0, length)}...`;
}

/**
 * Format a confidence score with color coding
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'text-green-600';
  if (confidence >= 0.7) return 'text-yellow-600';
  return 'text-red-600';
}

/**
 * Format a verification status
 */
export function formatVerificationStatus(status: string): {
  label: string;
  color: string;
  icon: string;
} {
  const statusMap = {
    genuine: {
      label: 'Genuine',
      color: 'text-green-600',
      icon: '✓',
    },
    counterfeit: {
      label: 'Counterfeit',
      color: 'text-red-600',
      icon: '✗',
    },
    suspicious: {
      label: 'Suspicious',
      color: 'text-yellow-600',
      icon: '⚠',
    },
    unknown: {
      label: 'Unknown',
      color: 'text-gray-600',
      icon: '?',
    },
  };
  
  return statusMap[status as keyof typeof statusMap] || statusMap.unknown;
}

