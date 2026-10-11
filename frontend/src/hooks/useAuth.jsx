import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { authApi } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }
    authApi
      .me()
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem('token')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo(() => {
    async function login(email, password) {
      const { data } = await authApi.login({ email, password })
      localStorage.setItem('token', data.access_token)
      const me = await authApi.me()
      setUser(me.data)
      return me.data
    }

    async function register(payload) {
      await authApi.register(payload)
      return login(payload.email, payload.password)
    }

    return {
      user,
      loading,
      login,
      register,
      logout() {
        localStorage.removeItem('token')
        setUser(null)
      },
    }
  }, [user, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
