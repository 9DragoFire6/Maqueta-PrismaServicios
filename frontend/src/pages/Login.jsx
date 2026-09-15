import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { mensajeError } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [codigo, setCodigo] = useState('')
  const [requiere2fa, setRequiere2fa] = useState(false)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setCargando(true)
    try {
      await login(email, password, requiere2fa ? codigo : undefined)
      navigate('/')
    } catch (err) {
      if (err?.response?.data?.requiere_2fa) {
        setRequiere2fa(true)
        setError(err.response.data.error || 'Ingresá el código de tu app de autenticación.')
      } else {
        setError(mensajeError(err))
      }
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-xl font-semibold text-gray-800">Gestión de Servicios</h1>
        <p className="mb-6 text-sm text-gray-500">Iniciá sesión para continuar.</p>
        <form onSubmit={enviar} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-gray-600">Email</label>
            <input
              type="email"
              required
              disabled={requiere2fa}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none disabled:bg-gray-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-600">Contraseña</label>
            <input
              type="password"
              required
              disabled={requiere2fa}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none disabled:bg-gray-100"
            />
          </div>
          {requiere2fa && (
            <div>
              <label className="mb-1 block text-sm text-gray-600">Código de autenticación</label>
              <input
                type="text"
                autoFocus
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
                placeholder="6 dígitos"
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
              />
            </div>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={cargando}
            className="w-full rounded bg-slate-800 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {requiere2fa ? 'Verificar código' : 'Ingresar'}
          </button>
        </form>
        <Link to="/recuperar-password" className="mt-4 block text-center text-sm text-slate-500 hover:underline">
          Olvidé mi contraseña
        </Link>
      </div>
    </div>
  )
}
