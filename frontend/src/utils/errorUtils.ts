import { AxiosError } from 'axios';

/**
 * Extract a user-friendly error message from any error type.
 * Handles Axios errors, standard errors, and unknown values.
 */
export function getErrorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (!error) return fallback;

  // Axios error with response from the server
  if (isAxiosError(error)) {
    // Network / connectivity error
    if (error.code === 'ERR_NETWORK' || !error.response) {
      return 'Unable to connect to the server. Please check your connection.';
    }
    if (error.code === 'ECONNABORTED') {
      return 'The request timed out. Please try again.';
    }

    const status = error.response.status;
    const detail = error.response.data?.detail;

    // Server returned a structured detail message
    if (detail) {
      if (typeof detail === 'string') return detail;
      // FastAPI validation errors come as array of { msg, loc, type }
      if (Array.isArray(detail)) {
        return detail.map((d: any) => d.msg || String(d)).join('. ');
      }
    }

    // Fallback by HTTP status code
    switch (status) {
      case 400: return 'Invalid request. Please check your input.';
      case 401: return 'Your session has expired. Please log in again.';
      case 403: return 'You do not have permission for this action.';
      case 404: return 'The requested resource was not found.';
      case 409: return 'A conflict occurred. The item may already exist.';
      case 413: return 'The file is too large. Please upload a smaller file.';
      case 422: return 'Invalid data. Please check the form fields.';
      case 429: return 'Too many requests. Please wait a moment.';
      case 503: return 'The service is temporarily unavailable. Please try again shortly.';
      default:
        if (status >= 500) return 'A server error occurred. Please try again later.';
        return fallback;
    }
  }

  // Standard Error object
  if (error instanceof Error) {
    // Don't expose raw technical messages to users
    if (error.message.includes('Network Error')) {
      return 'Unable to connect to the server. Please check your connection.';
    }
    if (error.message.includes('timeout')) {
      return 'The request timed out. Please try again.';
    }
    // For non-technical messages, return them
    if (error.message.length < 200 && !error.message.includes('at ') && !error.message.includes('Error:')) {
      return error.message;
    }
    return fallback;
  }

  // Plain string
  if (typeof error === 'string') {
    return error.length < 200 ? error : fallback;
  }

  return fallback;
}

function isAxiosError(error: unknown): error is AxiosError<{ detail?: string | any[] }> {
  return typeof error === 'object' && error !== null && 'isAxiosError' in error;
}
