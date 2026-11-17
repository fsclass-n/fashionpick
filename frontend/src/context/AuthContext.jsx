import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, tokenStore } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(tokenStore.get())
  const [loading, setLoading] = useState(!!tokenStore.get())

  const logout = useCallback(() => {
    tokenStore.clear()
    setToken(null)
    setUser(null)
  }, [])

  const acceptToken = useCallback(async (accessToken, knownUser) => {
    tokenStore.set(accessToken)
    setToken(accessToken)
    const me = knownUser || (await api('/api/auth/me'))
    setUser(me)
    return me
  }, [])

  useEffect(() => {
    if (!token) return
    api('/api/auth/me')
      .then(setUser)
      .catch(logout)
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    window.addEventListener('fp:unauthorized', logout)
    return () => window.removeEventListener('fp:unauthorized', logout)
  }, [logout])

  const login = useCallback(
    async (email, password) => {
      const res = await api('/api/auth/login', { method: 'POST', body: { email, password } })
      return acceptToken(res.access_token, res.user)
    },
    [acceptToken],
  )

  const register = useCallback(
    async (payload) => {
      const res = await api('/api/auth/register', { method: 'POST', body: payload })
      return acceptToken(res.access_token, res.user)
    },
    [acceptToken],
  )

  const testLogin = useCallback(
    async (role) => {
      const res = await api('/api/auth/test-login', { method: 'POST', body: { role } })
      return acceptToken(res.access_token, res.user)
    },
    [acceptToken],
  )

  const refresh = useCallback(() => api('/api/auth/me').then(setUser), [])

  const value = useMemo(
    () => ({ user, token, loading, isAdmin: user?.role === 'admin', login, register, testLogin, logout, acceptToken, refresh }),
    [user, token, loading, login, register, testLogin, logout, acceptToken, refresh],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
