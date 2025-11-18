/**
 * API Service Layer
 * Centralized API communication with type-safe methods
 */

import { apiRequest, apiUpload, ApiError } from '@/api/client';
import { API_ENDPOINTS } from '@/lib/config';

/**
 * Health Check Service
 */
export const HealthService = {
  /**
   * Check if the API is healthy
   */
  async checkHealth(): Promise<{ status: string; timestamp: string }> {
    return apiRequest(API_ENDPOINTS.health);
  },

  /**
   * Get detailed health information
   */
  async getDetailedHealth(): Promise<any> {
    return apiRequest(API_ENDPOINTS.healthDetailed);
  },
};

/**
 * Verification Service
 */
export const VerificationService = {
  /**
   * Verify an IC component
   */
  async verifyIC(data: {
    part_number: string;
    manufacturer?: string;
    image_data?: string;
  }): Promise<any> {
    return apiRequest(API_ENDPOINTS.verifyIC, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get verification result by ID
   */
  async getResult(id: number): Promise<any> {
    return apiRequest(API_ENDPOINTS.verificationResult(id));
  },

  /**
   * Get verification history
   */
  async getHistory(params?: {
    limit?: number;
    offset?: number;
  }): Promise<any> {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());
    
    const url = `${API_ENDPOINTS.verificationHistory}?${query.toString()}`;
    return apiRequest(url);
  },

  /**
   * Get list of manufacturers
   */
  async getManufacturers(): Promise<string[]> {
    return apiRequest(API_ENDPOINTS.manufacturers);
  },
};

/**
 * Image Service
 */
export const ImageService = {
  /**
   * Upload an image file
   */
  async uploadImage(file: File): Promise<{
    image_id: string;
    filename: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    return apiUpload(API_ENDPOINTS.imageUpload, formData);
  },

  /**
   * Analyze an uploaded image
   */
  async analyzeImage(imageId: string): Promise<any> {
    return apiRequest(API_ENDPOINTS.imageAnalyze(imageId), {
      method: 'POST',
    });
  },
};

/**
 * Video Session Service
 */
export const VideoSessionService = {
  /**
   * Start a new video session
   */
  async startSession(): Promise<{
    session_id: string;
    streamer_ws_path: string;
  }> {
    return apiRequest(API_ENDPOINTS.videoSessionStart, {
      method: 'POST',
    });
  },

  /**
   * Get active session information
   */
  async getActiveSession(): Promise<{
    active: boolean;
    session_id?: string;
    viewer_ws_path?: string;
    started_at?: string;
  }> {
    return apiRequest(API_ENDPOINTS.videoSessionActive);
  },

  /**
   * Get session status
   */
  async getSessionStatus(sessionId: string): Promise<any> {
    return apiRequest(API_ENDPOINTS.videoSessionStatus(sessionId));
  },
};

/**
 * Datasheet Service
 */
export const DatasheetService = {
  /**
   * Fetch datasheet for a part number
   */
  async fetchDatasheet(partNumber: string): Promise<any> {
    return apiRequest(API_ENDPOINTS.datasheetFetch(partNumber), {
      method: 'POST',
    });
  },
};

/**
 * Export all services
 */
export const ApiService = {
  health: HealthService,
  verification: VerificationService,
  image: ImageService,
  videoSession: VideoSessionService,
  datasheet: DatasheetService,
};

export { ApiError };

