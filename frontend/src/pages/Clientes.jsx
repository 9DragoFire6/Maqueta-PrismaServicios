import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { clientesApi } from '../api/dominio'
import { mensajeError } from '../api/client'
import Modal from '../components/Modal'

const VACIO = { nombre_contacto: '', telefono: '', email: '', direccion: '', nif: '', iva_porcentaje: 21 }

function FormularioCliente({ inicial, onGuardar, onCancelar, guardando, error }) {
  const [form, setForm] = useState(inicial)
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        onGuardar(form)
      }}
      className="space-y-3"
    >
      {[
        ['nombre_contacto', 'Nombre de contacto', true],
        ['nif', 'NIF', false],
        ['telefono', 'Teléfono', false],
        ['email', 'Email', false],
        ['direccion', 'Dirección', false],
      ].map(([campo, etiqueta, requerido]) => (
        <div key={campo}>
          <label className="mb-1 block text-sm text-gray-600">{etiqueta}</label>
          <input
            required={requerido}
            value={form[campo] || ''}
            onChange={(e) => setForm({ ...form, [campo]: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          />
        </div>
      ))}
      <div>
        <label className="mb-1 block text-sm text-gray-600">IVA %</label>
        <input
          type="number"
          step="0.01"
          value={form.iva_porcentaje}
          onChange={(e) => setForm({ ...form, iva_porcentaje: e.target.value })}
          className="w-32 rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <button type="button" onClick={onCancelar} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">
          Cancelar
        </button>
        <button type="submit" disabled={guardando} className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50">
          Guardar
        </button>
      </div>
    </form>
  )
}

export default function Clientes() {
  const qc = useQueryClient()
  const { data: clientes, isLoading } = useQuery({ queryKey: ['clientes'], queryFn: () => clientesApi.list() })
  const [modal, setModal] = useState(null) // null | 'crear' | cliente
  const [error, setError] = useState('')

  const guardar = useMutation({
    mutationFn: (form) => (modal.id ? clientesApi.update(modal.id, form) : clientesApi.create(form)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clientes'] })
      setModal(null)
      setError('')
    },
    onError: (err) => setError(mensajeError(err)),
  })

  async function anonimizar(cliente) {
    if (!confirm(`¿Anonimizar los datos personales de "${cliente.nombre_contacto}"? Los contratos e historial se conservan.`)) return
    await clientesApi.anonimizarDatos(cliente.id)
    qc.invalidateQueries({ queryKey: ['clientes'] })
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Clientes</h1>
        <button
          onClick={() => { setModal('crear'); setError('') }}
          className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700"
        >
          <Plus size={16} /> Nuevo cliente
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2">NIF</th>
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2">IVA %</th>
              <th className="px-4 py-2">Activa</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td className="px-4 py-3 text-gray-400" colSpan={6}>Cargando…</td></tr>
            )}
            {clientes?.map((c) => (
              <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2">{c.nombre_contacto}</td>
                <td className="px-4 py-2">{c.nif}</td>
                <td className="px-4 py-2">{c.email}</td>
                <td className="px-4 py-2">{c.iva_porcentaje}</td>
                <td className="px-4 py-2">{c.activa ? 'Sí' : 'No'}</td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => { setModal(c); setError('') }} className="mr-3 text-slate-600 hover:underline">
                    Editar
                  </button>
                  <button onClick={() => anonimizar(c)} className="text-red-600 hover:underline">
                    Anonimizar
                  </button>
                </td>
              </tr>
            ))}
            {clientes?.length === 0 && (
              <tr><td className="px-4 py-3 text-gray-400" colSpan={6}>No hay clientes todavía.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal titulo={modal === 'crear' ? 'Nuevo cliente' : 'Editar cliente'} onClose={() => setModal(null)}>
          <FormularioCliente
            inicial={modal === 'crear' ? VACIO : modal}
            onGuardar={(form) => guardar.mutate(form)}
            onCancelar={() => setModal(null)}
            guardando={guardar.isPending}
            error={error}
          />
        </Modal>
      )}
    </div>
  )
}
