// JWT Token Management

const TOKEN_KEY = 'token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated() {
  return !!getToken();
}

// Check if dev mode is enabled (for auto-login)
export async function checkDevMode() {
  try {
    const response = await fetch('/api/auth/dev-mode');
    if (response.ok) {
      const data = await response.json();
      return data.enabled;
    }
  } catch (e) {
    // Dev mode endpoint not available
  }
  return false;
}

// Redirect to login if not authenticated
export function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = '/login.html';
    return false;
  }
  return true;
}

// Redirect to app if already authenticated
export function redirectIfAuthenticated() {
  if (isAuthenticated()) {
    window.location.href = '/';
    return true;
  }
  return false;
}

// Add auth header to fetch requests
export async function fetchWithAuth(url, options = {}) {
  const token = getToken();
  const headers = {
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 - token expired or invalid
  if (response.status === 401) {
    clearToken();
    window.location.href = '/login.html';
    throw new Error('Session expired');
  }

  return response;
}

// Logout
export function logout() {
  clearToken();
  window.location.href = '/login.html';
}

// Setup HTMX to include auth header on all requests
export function setupHTMXAuth() {
  document.body.addEventListener('htmx:configRequest', (event) => {
    const token = getToken();
    if (token) {
      event.detail.headers['Authorization'] = `Bearer ${token}`;
    }
  });

  // Handle 401 responses from HTMX
  document.body.addEventListener('htmx:responseError', (event) => {
    if (event.detail.xhr.status === 401) {
      clearToken();
      window.location.href = '/login.html';
    }
  });
}

// Handle auth form submission (login/register)
export function handleAuthResponse(event) {
  const xhr = event.detail.xhr;

  if (xhr.status === 200) {
    try {
      const data = JSON.parse(xhr.response);
      if (data.access_token) {
        setToken(data.access_token);
        window.location.href = '/';
        return true;
      }
    } catch (e) {
      console.error('Failed to parse auth response:', e);
    }
  }
  return false;
}
