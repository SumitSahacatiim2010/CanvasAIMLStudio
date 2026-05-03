// Unified API utility using native fetch — with automatic dev-token auth

const API_BASE = 'http://localhost:8000/api/v1';
const AUTH_BASE = 'http://localhost:8000';

// Module-level JWT cache
let _cachedToken: string | null = null;
let _tokenPromise: Promise<string> | null = null;

/**
 * Fetch a development JWT token from the gateway.
 * Caches the result so only one request is made per session.
 */
async function getDevToken(): Promise<string> {
  if (_cachedToken) return _cachedToken;

  // Avoid concurrent token fetches (multiple components mounting at once)
  if (_tokenPromise) return _tokenPromise;

  _tokenPromise = (async () => {
    try {
      const res = await fetch(`${AUTH_BASE}/auth/dev-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`Dev-token request failed: ${res.status}`);
      }
      const data = await res.json();
      _cachedToken = data.access_token;
      console.log('[Auth] Dev token acquired ✓');
      return _cachedToken!;
    } catch (err) {
      _tokenPromise = null; // Allow retry on failure
      throw err;
    }
  })();

  return _tokenPromise;
}

/**
 * Invalidate the cached token (e.g. on 401 response).
 */
export function clearAuthToken(): void {
  _cachedToken = null;
  _tokenPromise = null;
}

/**
 * Primary API client. Automatically acquires a dev JWT and attaches it.
 */
export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const token = await getDevToken();
  const url = `${API_BASE}${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  // If token expired, clear cache and retry once
  if (response.status === 401) {
    clearAuthToken();
    const freshToken = await getDevToken();
    const retryConfig: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        'Authorization': `Bearer ${freshToken}`,
        ...options.headers,
      },
    };
    const retryResponse = await fetch(url, retryConfig);
    if (!retryResponse.ok) {
      const errorData = await retryResponse.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Request failed: ${retryResponse.status} ${retryResponse.statusText}`);
    }
    return retryResponse.json();
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
