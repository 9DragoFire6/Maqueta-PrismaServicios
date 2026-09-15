import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/auth'
import { mensajeError } from '../api/client'

export default function RecuperarPassword() {
  const [email, setEmail] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    setError('')
    try {
      const r = await authApi.solicitarRecuperacion(email)
      setMensaje(r.mensaje)
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-xl font-semibold text-gray-800">Recuperar contraseña</h1>
        <p className="mb-6 text-sm text-gray-500">Te enviamos un enlace para restablecerla (revisá la consola del backend: no hay proveedor de correo real conectado).</p>
        {mensaje ? (
          <p className="text-sm text-green-700">{mensaje}</p>
        ) : (
          <form onSubmit={enviar} className="space-y-4">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Tu email"
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button type="submit" className="w-full rounded bg-slate-800 py-2 text-sm font-medium text-white hover:bg-slate-700">
              Enviar enlace
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
