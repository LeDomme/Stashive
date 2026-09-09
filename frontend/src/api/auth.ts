export interface AuthStatus { setup_required: boolean; authenticated: boolean }
export interface CurrentUser { id: number; username: string; display_name: string | null; is_instance_admin: boolean }

function csrfToken(): string | undefined {
  return document.cookie.split('; ').find((entry) => entry.startsWith('stashive_csrf='))?.split('=')[1]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: 'same-origin', ...init })
  if (!response.ok) throw new Error('Authentication request failed: ' + response.status)
  return (await response.json()) as T
}

export const fetchAuthStatus = (): Promise<AuthStatus> => request('/api/auth/status')
export const fetchCurrentUser = (): Promise<CurrentUser> => request('/api/auth/me')
export const login = (username: string, password: string): Promise<CurrentUser> =>
  request('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) })
export const setup = (token: string, username: string, displayName: string, password: string): Promise<CurrentUser> =>
  request('/api/auth/setup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token, username, display_name: displayName || null, password }) })
export async function logout(): Promise<void> {
  const response = await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRF-Token': csrfToken() ?? '' } })
  if (!response.ok) throw new Error('Logout failed: ' + response.status)
}
