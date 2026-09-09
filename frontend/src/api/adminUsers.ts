import { request } from '@/api/client'

export interface AdminUser {
  id: number
  username: string
  display_name: string | null
  is_instance_admin: boolean
  is_active: boolean
  created_at: string
}

export interface CreateAdminUserPayload {
  username: string
  display_name: string | null
  password: string
  is_instance_admin: boolean
}

export interface UpdateAdminUserPayload {
  display_name?: string | null
  is_instance_admin?: boolean
  is_active?: boolean
}

export const listAdminUsers = (): Promise<AdminUser[]> => request('/api/admin/users')
export const createAdminUser = (payload: CreateAdminUserPayload): Promise<AdminUser> =>
  request('/api/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
export const updateAdminUser = (
  userId: number,
  payload: UpdateAdminUserPayload,
): Promise<AdminUser> =>
  request(`/api/admin/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
export const resetAdminUserPassword = (userId: number, password: string): Promise<AdminUser> =>
  request(`/api/admin/users/${userId}/password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
