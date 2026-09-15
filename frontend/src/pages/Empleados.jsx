import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { mensajeError } from '../api/client'
import { empleadosApi } from '../api/dominio'
import { useAuth } from '../context/AuthContext'
import Modal from '../components/Modal'

const VACIO = { nombre: '', apellido: '', email: '', telefono: '', categoria: 'estandar', especialidad: '', observaciones: '' }

function FormularioEmpleado({ inicial, onGuardar, onCancelar, error }) {
  const [form, setForm] = useState(inicial)
  return (
    <form onSubmit={(e) => { e.preventDefault(); onGuardar(form) }} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm text-gray-600">Nombre</label>
          <input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">Apellido</label>
          <input value={form.apellido} onChange={(e) => setForm({ ...form, apellido: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm text-gray-600">Email</label>
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">Teléfono</label>
          <input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm text-gray-600">Categoría</label>
          <input required value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">Especialidad</label>
          <input value={form.especialidad} onChange={(e) => setForm({ ...form, especialidad: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-sm text-gray-600">Observaciones</label>
        <textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" rows={2} />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <button type="button" onClick={onCancelar} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
        <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Guardar</button>
      </div>
    </form>
  )
}

export default function Empleados() {
  const { esAdmin } = useAuth()
  const qc = useQueryClient()
  const { data: empleados, isLoading } = useQuery({ queryKey: ['empleados'], queryFn: () => empleadosApi.list() })
  const [modal, setModal] = useState(null)
  const [error, setError] = useState('')

  const guardar = useMutation({
    mutationFn: (form) => (modal.id ? empleadosApi.update(modal.id, form) : empleadosApi.create(form)),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['empleados'] }); setModal(null); setError('') },
    onError: (err) => setError(mensajeError(err)),
  })

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Empleados</h1>
        {esAdmin && (
          <button onClick={() => { setModal('crear'); setError('') }} className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">
            <Plus size={16} /> Nuevo empleado
          </button>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2">Categoría</th>
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2">Teléfono</th>
              <th className="px-4 py-2">Activo</th>
              {esAdmin && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="px-4 py-3 text-gray-400" colSpan={6}>Cargando…</td></tr>}
            {empleados?.map((e) => (
              <tr key={e.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="flex items-center gap-2 px-4 py-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: e.color }} />
                  {e.nombre} {e.apellido}
                </td>
                <td className="px-4 py-2">{e.categoria}</td>
                <td className="px-4 py-2">{e.email}</td>
                <td className="px-4 py-2">{e.telefono}</td>
                <td className="px-4 py-2">{e.activo ? 'Sí' : 'No'}</td>
                {esAdmin && (
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => { setModal(e); setError('') }} className="text-slate-600 hover:underline">Editar</button>
                  </td>
                )}
              </tr>
            ))}
            {empleados?.length === 0 && <tr><td className="px-4 py-3 text-gray-400" colSpan={6}>No hay empleados todavía.</td></tr>}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal titulo={modal === 'crear' ? 'Nuevo empleado' : 'Editar empleado'} onClose={() => setModal(null)} ancho="max-w-xl">
          <FormularioEmpleado inicial={modal === 'crear' ? VACIO : modal} onGuardar={(form) => guardar.mutate(form)} onCancelar={() => setModal(null)} error={error} />
        </Modal>
      )}
    </div>
  )
}
