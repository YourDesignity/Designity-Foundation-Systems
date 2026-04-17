/**
 * Extracts a user-friendly message from API errors.
 * Supports FastAPI detail/message patterns with safe fallbacks.
 * @param {any} error
 * @returns {string}
 */
export const extractErrorMessage = (error) => {
  if (!error) return 'An unexpected error occurred.';

  const responseData = error?.response?.data;

  if (typeof responseData === 'string' && responseData.trim()) {
    return responseData;
  }

  if (Array.isArray(responseData?.detail)) {
    return responseData.detail
      .map((item) => item?.msg || item?.message || JSON.stringify(item))
      .join(', ');
  }

  if (responseData?.detail) {
    return String(responseData.detail);
  }

  if (responseData?.message) {
    return String(responseData.message);
  }

  if (error?.message) {
    return String(error.message);
  }

  return 'An unexpected error occurred.';
};

/**
 * Normalizes API errors for consistent UI handling.
 * @param {any} error
 * @returns {{ status: number | null, message: string, raw: any }}
 */
export const formatApiError = (error) => ({
  status: error?.response?.status ?? null,
  message: extractErrorMessage(error),
  raw: error,
});

/**
 * Returns true if error appears to be a network-level failure.
 * @param {any} error
 * @returns {boolean}
 */
export const isNetworkError = (error) => !error?.response && Boolean(error?.request || error?.message);
