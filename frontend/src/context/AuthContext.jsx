import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getMe, getToken, setToken, clearAuth as clearAuthStorage } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }

    try {
      const userData = await getMe()
      setUser(userData)
    } catch {
      clearAuthStorage()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = useCallback((token, userData) => {
    setToken(token)
    setUser(userData)
  }, [])

  const logout = useCallback(() => {
    clearAuthStorage()
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    try {
      const userData = await getMe()
      setUser(userData)
    } catch {
      // Silently fail — user will see stale data
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
