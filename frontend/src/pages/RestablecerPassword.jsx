import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { authApi } from '../api/auth'
import { mensajeError } from '../api/client'

export default function RestablecerPassword() {
  const { uid, token } = useParams()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [listo, setListo] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    try {
      await authApi.restablecerPassword(uid, token, password)
      setListo(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-gray-800">Elegí una nueva contraseña</h1>
        {listo ? (
          <p className="text-sm text-green-700">Contraseña restablecida. Redirigiendo al inicio de sesión…</p>
        ) : (
          <form onSubmit={enviar} className="space-y-4">
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Nueva contraseña"
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button type="submit" className="w-full rounded bg-slate-800 py-2 text-sm font-medium text-white hover:bg-slate-700">
              Restablecer
            </button>
          </form>
        )}
        <Link to="/login" className="mt-4 block text-center text-sm text-slate-500 hover:underline">
          Volver a iniciar sesión
        </Link>
      </div>
    </div>
  )
}
