/** Shared same-origin API request helpers. */

export class ApiError extends Error {
  constructor(readonly status: number) {
    super(`API request failed: ${status}`)
  }
}

function csrfToken(): string | undefined {
  return document.cookie
    .split('; ')
    .find((entry) => entry.startsWith('stashive_csrf='))
    ?.split('=')[1]
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  const method = init?.method?.toUpperCase()
  if (method && !['GET', 'HEAD'].includes(method)) {
    headers.set('X-CSRF-Token', csrfToken() ?? '')
  }
  const response = await fetch(path, { credentials: 'same-origin', ...init, headers })
  if (!response.ok) throw new ApiError(response.status)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
