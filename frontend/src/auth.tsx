import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

export type User = {
  id: number
  first_name: string
  last_name: string
  email: string
}

type AuthValue = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
}

export type RegisterData = {
  first_name: string
  last_name: string
  email: string
  password: string
}

const AuthContext = createContext<AuthValue | null>(null)

async function post(path: string, body?: unknown) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(readDetail(detail) ?? 'Something went wrong. Try again.')
  }
  return res.status === 204 ? null : res.json()
}

// FastAPI returns a plain string for our own errors and an array of field errors
// for validation failures; this flattens both into one message for the form.
function readDetail(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') return null
  const detail = (payload as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string } | undefined
    return first?.msg ?? null
  }
  return null
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/auth/me')
      .then((r) => (r.ok ? r.json() : null))
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const value: AuthValue = {
    user,
    loading,
    login: async (email, password) => {
      setUser(await post('/api/auth/login', { email, password }))
    },
    register: async (data) => {
      setUser(await post('/api/auth/register', data))
    },
    logout: async () => {
      await post('/api/auth/logout')
      setUser(null)
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
