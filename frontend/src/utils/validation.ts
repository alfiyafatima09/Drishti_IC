/**
 * Validation utility functions
 */

import { FILE_UPLOAD } from '@/constants';

/**
 * Validate if a file is an accepted image type
 */
export function isValidImageFile(file: File): boolean {
  return FILE_UPLOAD.ACCEPTED_TYPES.includes(file.type as any);
}

/**
 * Validate if a file size is within limits
 */
export function isValidFileSize(file: File): boolean {
  return file.size <= FILE_UPLOAD.MAX_SIZE;
}

/**
 * Validate an image file (type and size)
 */
export function validateImageFile(file: File): {
  valid: boolean;
  error?: string;
} {
  if (!isValidImageFile(file)) {
    return {
      valid: false,
      error: `Invalid file type. Accepted types: ${FILE_UPLOAD.ACCEPTED_EXTENSIONS.join(', ')}`,
    };
  }
  
  if (!isValidFileSize(file)) {
    return {
      valid: false,
      error: `File size exceeds ${FILE_UPLOAD.MAX_SIZE / (1024 * 1024)}MB limit`,
    };
  }
  
  return { valid: true };
}

/**
 * Validate a part number format
 */
export function isValidPartNumber(partNumber: string): boolean {
  // Basic validation: alphanumeric with some special characters
  return /^[A-Z0-9\-_]+$/i.test(partNumber);
}

/**
 * Validate an email address
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

