import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { mensajeError } from '../api/client'
import { serviciosApi } from '../api/dominio'
import DobleVerificacionModal from '../components/DobleVerificacionModal'
import Modal from '../components/Modal'

const VACIO = {
  codigo: '', nombre: '', categoria: 'estandar', tarifa_cliente: '',
  compensacion_tipo: 'por_hora', compensacion_valor: '', cruza_medianoche: false, precio_manual: false, notas: '',
}

function FormularioServicio({ inicial, onListo, onCancelar }) {
  const [form, setForm] = useState(inicial)
  const [pedirVerificacion, setPedirVerificacion] = useState(false)

  return (
    <>
      <form
        onSubmit={(e) => { e.preventDefault(); setPedirVerificacion(true) }}
        className="space-y-3"
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm text-gray-600">Código</label>
            <input required value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-600">Categoría</label>
            <input required value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">Nombre</label>
          <input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm text-gray-600">Tarifa al cliente (por hora)</label>
            <input required type="number" step="0.01" value={form.tarifa_cliente}
              onChange={(e) => setForm({ ...form, tarifa_cliente: e.target.value })}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-600">Compensación</label>
            <select value={form.compensacion_tipo} onChange={(e) => setForm({ ...form, compensacion_tipo: e.target.value })}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none">
              <option value="por_hora">Por hora</option>
              <option value="porcentaje_base">% de lo facturado</option>
            </select>
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">
            {form.compensacion_tipo === 'por_hora' ? 'Importe por hora para el empleado' : 'Porcentaje (0-100) para el empleado'}
          </label>
          <input required type="number" step="0.01" value={form.compensacion_valor}
            onChange={(e) => setForm({ ...form, compensacion_valor: e.target.value })}
            className="w-40 rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" />
        </div>
        <div className="flex gap-4 text-sm text-gray-600">
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={form.cruza_medianoche} onChange={(e) => setForm({ ...form, cruza_medianoche: e.target.checked })} />
            Cruza medianoche
          </label>
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={form.precio_manual} onChange={(e) => setForm({ ...form, precio_manual: e.target.checked })} />
            Precio manual
          </label>
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">Notas</label>
          <textarea value={form.notas} onChange={(e) => setForm({ ...form, notas: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none" rows={2} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onCancelar} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
          <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Guardar</button>
        </div>
      </form>
      {pedirVerificacion && (
        <DobleVerificacionModal
          onClose={() => setPedirVerificacion(false)}
          onConfirmado={(datosVerificacion) => onListo({ ...form, ...datosVerificacion })}
        />
      )}
    </>
  )
}

export default function Servicios() {
  const qc = useQueryClient()
  const { data: servicios, isLoading } = useQuery({ queryKey: ['servicios'], queryFn: () => serviciosApi.list() })
  const [modal, setModal] = useState(null)
  const [error, setError] = useState('')

  const guardar = useMutation({
    mutationFn: (form) => (modal.id ? serviciosApi.update(modal.id, form) : serviciosApi.create(form)),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['servicios'] }); setModal(null); setError('') },
    onError: (err) => setError(mensajeError(err)),
  })

  async function desactivar(servicio) {
    const mensaje = servicio.en_uso
      ? `"${servicio.nombre}" se desactivará (tiene historial, no se puede borrar). ¿Continuar?`
      : `"${servicio.nombre}" nunca se usó: se eliminará por completo. ¿Continuar?`
    if (!confirm(mensaje)) return
    await serviciosApi.desactivar(servicio.id)
    qc.invalidateQueries({ queryKey: ['servicios'] })
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Servicios</h1>
        <button onClick={() => { setModal('crear'); setError('') }} className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">
          <Plus size={16} /> Nuevo servicio
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Código</th>
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2">Categoría</th>
              <th className="px-4 py-2">Tarifa cliente</th>
              <th className="px-4 py-2">Compensación</th>
              <th className="px-4 py-2">Activo</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="px-4 py-3 text-gray-400" colSpan={7}>Cargando…</td></tr>}
            {servicios?.map((s) => (
              <tr key={s.id} className={`border-b border-gray-100 hover:bg-gray-50 ${!s.activo ? 'opacity-50' : ''}`}>
                <td className="px-4 py-2">{s.codigo}</td>
                <td className="px-4 py-2">{s.nombre}</td>
                <td className="px-4 py-2">{s.categoria}</td>
                <td className="px-4 py-2">{s.tarifa_cliente}</td>
                <td className="px-4 py-2">
                  {s.compensacion_tipo === 'por_hora' ? `${s.compensacion_valor}/h` : `${s.compensacion_valor}% de lo facturado`}
                </td>
                <td className="px-4 py-2">{s.activo ? 'Sí' : 'No'}</td>
                <td className="px-4 py-2 text-right">
                  {s.activo && (
                    <>
                      <button onClick={() => { setModal(s); setError('') }} className="mr-3 text-slate-600 hover:underline">Editar</button>
                      <button onClick={() => desactivar(s)} className="text-red-600 hover:underline">Desactivar</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {servicios?.length === 0 && <tr><td className="px-4 py-3 text-gray-400" colSpan={7}>No hay servicios todavía.</td></tr>}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal titulo={modal === 'crear' ? 'Nuevo servicio' : 'Editar servicio'} onClose={() => setModal(null)} ancho="max-w-xl">
          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          <FormularioServicio inicial={modal === 'crear' ? VACIO : modal} onListo={(form) => guardar.mutate(form)} onCancelar={() => setModal(null)} />
        </Modal>
      )}
    </div>
  )
}
