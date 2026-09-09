import { request } from '@/api/client'

export interface AuthStatus { setup_required: boolean; authenticated: boolean }
export interface CurrentUser { id: number; username: string; display_name: string | null; is_instance_admin: boolean }

export const fetchAuthStatus = (): Promise<AuthStatus> => request('/api/auth/status')
export const fetchCurrentUser = (): Promise<CurrentUser> => request('/api/auth/me')
export const login = (username: string, password: string): Promise<CurrentUser> =>
  request('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) })
export const setup = (token: string, username: string, displayName: string, password: string): Promise<CurrentUser> =>
  request('/api/auth/setup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token, username, display_name: displayName || null, password }) })
export async function logout(): Promise<void> {
  await request<void>('/api/auth/logout', { method: 'POST' })
}
