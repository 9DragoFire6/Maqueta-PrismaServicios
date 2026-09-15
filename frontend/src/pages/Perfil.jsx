import { useState } from 'react'
import { authApi } from '../api/auth'
import { mensajeError } from '../api/client'
import { useAuth } from '../context/AuthContext'

function SeccionDatos() {
  const { usuario, actualizarUsuarioLocal } = useAuth()
  const [form, setForm] = useState(usuario)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  async function guardar(e) {
    e.preventDefault()
    setError('')
    setMensaje('')
    try {
      const actualizado = await authApi.actualizarPerfil({
        first_name: form.first_name, last_name: form.last_name, email: form.email,
        nif: form.nif, direccion: form.direccion, nacionalidad: form.nacionalidad,
      })
      actualizarUsuarioLocal(actualizado)
      setMensaje('Datos actualizados.')
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <form onSubmit={guardar} className="max-w-md space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm text-gray-600">Nombre</label>
          <input value={form.first_name || ''} onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">Apellido</label>
          <input value={form.last_name || ''} onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-sm text-gray-600">Email</label>
        <input type="email" value={form.email || ''} onChange={(e) => setForm({ ...form, email: e.target.value })}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-sm text-gray-600">NIF</label>
        <input value={form.nif || ''} onChange={(e) => setForm({ ...form, nif: e.target.value })}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-sm text-gray-600">Dirección</label>
        <input value={form.direccion || ''} onChange={(e) => setForm({ ...form, direccion: e.target.value })}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
      </div>
      {mensaje && <p className="text-sm text-green-700">{mensaje}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Guardar</button>
    </form>
  )
}

function SeccionPassword() {
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  async function cambiar(e) {
    e.preventDefault()
    setError('')
    setMensaje('')
    try {
      const r = await authApi.cambiarPassword(actual, nueva)
      setMensaje(r.mensaje)
      setActual('')
      setNueva('')
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <form onSubmit={cambiar} className="max-w-md space-y-3">
      <input type="password" required placeholder="Contraseña actual" value={actual} onChange={(e) => setActual(e.target.value)}
        className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
      <input type="password" required placeholder="Nueva contraseña" value={nueva} onChange={(e) => setNueva(e.target.value)}
        className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
      {mensaje && <p className="text-sm text-green-700">{mensaje}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Cambiar contraseña</button>
    </form>
  )
}

function Seccion2FA() {
  const [estado, setEstado] = useState(null)
  const [qr, setQr] = useState(null)
  const [codigo, setCodigo] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  useState(() => { authApi.estado2fa().then((r) => setEstado(r.activo)) })

  async function iniciarSetup() {
    setError('')
    const r = await authApi.setup2fa()
    setQr(r.qr_code)
  }

  async function confirmar(e) {
    e.preventDefault()
    setError('')
    try {
      await authApi.verificar2fa(codigo)
      setQr(null)
      setEstado(true)
      setMensaje('2FA activado correctamente.')
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  if (estado === null) return null

  return (
    <div className="max-w-md space-y-3">
      {estado && !qr && <p className="text-sm text-green-700">La verificación en dos pasos ya está activa.</p>}
      {mensaje && <p className="text-sm text-green-700">{mensaje}</p>}
      {!qr && (
        <button onClick={iniciarSetup} className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">
          {estado ? 'Reconfigurar 2FA' : 'Activar 2FA'}
        </button>
      )}
      {qr && (
        <form onSubmit={confirmar} className="space-y-3">
          <img src={qr} alt="Código QR" className="h-40 w-40 rounded border border-gray-200" />
          <input required placeholder="Código de 6 dígitos" value={codigo} onChange={(e) => setCodigo(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Confirmar</button>
        </form>
      )}
    </div>
  )
}

export default function Perfil() {
  const [tab, setTab] = useState('datos')

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-gray-800">Mi perfil</h1>
      <div className="mb-6 flex gap-4 border-b border-gray-200 text-sm">
        {[['datos', 'Datos'], ['password', 'Contraseña'], ['2fa', 'Autenticación en dos pasos']].map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)}
            className={`-mb-px border-b-2 px-1 py-2 ${tab === id ? 'border-slate-800 text-slate-800' : 'border-transparent text-gray-500'}`}>
            {label}
          </button>
        ))}
      </div>
      {tab === 'datos' && <SeccionDatos />}
      {tab === 'password' && <SeccionPassword />}
      {tab === '2fa' && <Seccion2FA />}
    </div>
  )
}
