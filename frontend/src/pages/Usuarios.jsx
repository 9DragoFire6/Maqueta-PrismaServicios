import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { authApi } from '../api/auth'
import { mensajeError } from '../api/client'
import Modal from '../components/Modal'

const VACIO = { username: '', email: '', first_name: '', last_name: '', rol: 'empleado' }

function FormularioUsuario({ onCreado, onCancelar }) {
  const [form, setForm] = useState(VACIO)
  const [error, setError] = useState('')
  const [mensaje, setMensaje] = useState('')

  async function enviar(e) {
    e.preventDefault()
    setError('')
    try {
      const r = await authApi.crearUsuario(form)
      setMensaje(r.mensaje)
      onCreado()
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  if (mensaje) return <p className="text-sm text-green-700">{mensaje}</p>

  return (
    <form onSubmit={enviar} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <input required placeholder="Usuario" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}
          className="rounded border border-gray-300 px-3 py-2 text-sm" />
        <input required type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
          className="rounded border border-gray-300 px-3 py-2 text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <input required placeholder="Nombre" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          className="rounded border border-gray-300 px-3 py-2 text-sm" />
        <input placeholder="Apellido" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          className="rounded border border-gray-300 px-3 py-2 text-sm" />
      </div>
      <select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
        <option value="empleado">Empleado</option>
        <option value="admin">Administrador</option>
      </select>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <button type="button" onClick={onCancelar} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
        <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Crear</button>
      </div>
    </form>
  )
}

export default function Usuarios() {
  const qc = useQueryClient()
  const { data: usuarios, isLoading } = useQuery({ queryKey: ['usuarios'], queryFn: () => authApi.listaUsuarios() })
  const [modal, setModal] = useState(false)

  const toggleActivo = useMutation({
    mutationFn: ({ id, is_active }) => authApi.actualizarUsuario(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['usuarios'] }),
  })

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Usuarios</h1>
        <button onClick={() => setModal(true)} className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">
          <Plus size={16} /> Nuevo usuario
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Usuario</th>
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2">Rol</th>
              <th className="px-4 py-2">Activo</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="px-4 py-3 text-gray-400" colSpan={6}>Cargando…</td></tr>}
            {usuarios?.map((u) => (
              <tr key={u.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2">{u.username}</td>
                <td className="px-4 py-2">{u.first_name} {u.last_name}</td>
                <td className="px-4 py-2">{u.email}</td>
                <td className="px-4 py-2">{u.rol}</td>
                <td className="px-4 py-2">{u.is_active ? 'Sí' : 'No'}</td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => toggleActivo.mutate({ id: u.id, is_active: !u.is_active })} className="text-slate-600 hover:underline">
                    {u.is_active ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal titulo="Nuevo usuario" onClose={() => setModal(false)} ancho="max-w-md">
          <FormularioUsuario onCreado={() => qc.invalidateQueries({ queryKey: ['usuarios'] })} onCancelar={() => setModal(false)} />
        </Modal>
      )}
    </div>
  )
}
