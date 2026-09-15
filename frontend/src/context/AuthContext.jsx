import { createContext, useContext, useMemo, useState } from 'react'
import { authApi } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(() => {
    const raw = localStorage.getItem('usuario')
    return raw ? JSON.parse(raw) : null
  })

  async function login(email, password, codigo_2fa) {
    const data = await authApi.login(email, password, codigo_2fa)
    localStorage.setItem('access', data.access)
    localStorage.setItem('refresh', data.refresh)
    const perfil = await authApi.perfil()
    localStorage.setItem('usuario', JSON.stringify(perfil))
    setUsuario(perfil)
    return perfil
  }

  async function logout() {
    const refresh = localStorage.getItem('refresh')
    try {
      if (refresh) await authApi.logout(refresh)
    } catch {
      // Si el token ya vencio o el logout falla, igual limpiamos la sesion local.
    }
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    localStorage.removeItem('usuario')
    setUsuario(null)
  }

  function actualizarUsuarioLocal(perfil) {
    localStorage.setItem('usuario', JSON.stringify(perfil))
    setUsuario(perfil)
  }

  const value = useMemo(
    () => ({ usuario, login, logout, actualizarUsuarioLocal, esAdmin: usuario?.rol === 'admin' }),
    [usuario],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
