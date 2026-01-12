// Session + CSRF management

const CSRF_KEY = 'csrf_token';
let cachedSession = null;

function isUnsafeMethod(method) {
  const m = (method || 'GET').toUpperCase();
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(m);
}

export function getCsrfToken() {
  return sessionStorage.getItem(CSRF_KEY);
}

export function setCsrfToken(token) {
  if (token) {
    sessionStorage.setItem(CSRF_KEY, token);
  } else {
    sessionStorage.removeItem(CSRF_KEY);
  }
}

export function clearSession() {
  cachedSession = null;
  setCsrfToken(null);
}

export async function getSession() {
  if (cachedSession) return cachedSession;

  try {
    const response = await fetch('/api/auth/session', {
      credentials: 'same-origin',
      cache: 'no-store',
    });

    if (!response.ok) {
      clearSession();
      return { authenticated: false };
    }

    const data = await response.json();
    if (data && data.authenticated) {
      cachedSession = data;
      if (data.csrf_token) {
        setCsrfToken(data.csrf_token);
      }
      return data;
    }
  } catch (e) {
    // Ignore errors, treat as unauthenticated
  }

  clearSession();
  return { authenticated: false };
}

export async function requireAuth() {
  const session = await getSession();
  if (!session.authenticated) {
    window.location.href = '/login.html';
    return null;
  }
  return session;
}

export async function redirectIfAuthenticated() {
  const session = await getSession();
  if (session.authenticated) {
    window.location.href = '/';
    return true;
  }
  return false;
}

export async function fetchWithAuth(url, options = {}) {
  const headers = {
    ...options.headers,
  };

  if (isUnsafeMethod(options.method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'same-origin',
  });

  if (response.status === 401) {
    clearSession();
    window.location.href = '/login.html';
    throw new Error('Session expired');
  }

  if (response.status === 403 && isUnsafeMethod(options.method)) {
    // Attempt to refresh CSRF token once
    await refreshCsrfToken();
  }

  return response;
}

export async function refreshCsrfToken() {
  try {
    const response = await fetch('/api/auth/csrf', {
      credentials: 'same-origin',
      cache: 'no-store',
    });
    if (response.ok) {
      const data = await response.json();
      if (data.csrf_token) {
        setCsrfToken(data.csrf_token);
      }
    }
  } catch (e) {
    // Ignore
  }
}

export async function logout() {
  try {
    await fetchWithAuth('/api/auth/logout', { method: 'POST' });
  } catch (e) {
    // Ignore
  }
  clearSession();
  window.location.href = '/login.html';
}
