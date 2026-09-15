import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { mensajeError } from '../api/client'
import { ausenciasApi, empleadosApi, turnosApi } from '../api/dominio'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

function FilaTurno({ turno, esAdmin }) {
  const qc = useQueryClient()
  const [horas, setHoras] = useState(turno.horas_reales ?? '')

  const registrar = useMutation({
    mutationFn: () => turnosApi.registrarHoras(turno.id, horas),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['turnos'] }),
    onError: (err) => alert(mensajeError(err)),
  })

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="px-4 py-2">{turno.fecha}</td>
      {esAdmin && <td className="px-4 py-2">Empleado #{turno.empleado}</td>}
      <td className="px-4 py-2">{turno.hora_inicio?.slice(0, 5)}–{turno.hora_fin?.slice(0, 5)}</td>
      <td className="px-4 py-2">
        {turno.marca === 'ausencia_automatica' && <span className="text-amber-600">Ausencia</span>}
        {turno.marca === 'autorizado' && <span className="text-blue-600">Autorizado</span>}
      </td>
      <td className="px-4 py-2">
        <div className="flex items-center gap-2">
          <input
            type="number" step="0.5" value={horas} onChange={(e) => setHoras(e.target.value)}
            disabled={turno.confirmado_por_empleado && !esAdmin}
            className="w-20 rounded border border-gray-300 px-2 py-1 text-sm disabled:bg-gray-100"
          />
          <button
            onClick={() => registrar.mutate()}
            disabled={registrar.isPending || horas === ''}
            className="rounded bg-slate-800 px-2 py-1 text-xs text-white hover:bg-slate-700 disabled:opacity-50"
          >
            Guardar
          </button>
        </div>
      </td>
    </tr>
  )
}

function ModalNuevaAusencia({ empleados, onClose, onCreada }) {
  const [form, setForm] = useState({ empleado: '', fecha_inicio: '', fecha_fin: '', motivo: '', sustituto: '' })
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    try {
      await ausenciasApi.create({ ...form, sustituto: form.sustituto || null })
      onCreada()
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <Modal titulo="Nueva ausencia" onClose={onClose} ancho="max-w-sm">
      <form onSubmit={enviar} className="space-y-3">
        <select required value={form.empleado} onChange={(e) => setForm({ ...form, empleado: e.target.value })}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
          <option value="">Empleado ausente…</option>
          {empleados?.map((e) => <option key={e.id} value={e.id}>{e.nombre} {e.apellido}</option>)}
        </select>
        <div className="grid grid-cols-2 gap-2">
          <input type="date" required value={form.fecha_inicio} onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
            className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
          <input type="date" required value={form.fecha_fin} onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
            className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
        </div>
        <input required placeholder="Motivo" value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        <select value={form.sustituto} onChange={(e) => setForm({ ...form, sustituto: e.target.value })}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
          <option value="">Sin sustituto (permiso)</option>
          {empleados?.map((e) => <option key={e.id} value={e.id}>{e.nombre} {e.apellido}</option>)}
        </select>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
          <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Registrar</button>
        </div>
      </form>
    </Modal>
  )
}

export default function Turnos() {
  const { esAdmin } = useAuth()
  const qc = useQueryClient()
  const { data: turnos, isLoading } = useQuery({ queryKey: ['turnos'], queryFn: () => turnosApi.list() })
  const { data: ausencias } = useQuery({ queryKey: ['ausencias'], queryFn: () => ausenciasApi.list() })
  const { data: empleados } = useQuery({ queryKey: ['empleados'], queryFn: () => empleadosApi.list(), enabled: esAdmin })
  const [modalAusencia, setModalAusencia] = useState(false)

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-gray-800">{esAdmin ? 'Turnos' : 'Mis turnos'}</h1>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Fecha</th>
              {esAdmin && <th className="px-4 py-2">Empleado</th>}
              <th className="px-4 py-2">Horario</th>
              <th className="px-4 py-2">Marca</th>
              <th className="px-4 py-2">Horas reales</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="px-4 py-3 text-gray-400" colSpan={5}>Cargando…</td></tr>}
            {turnos?.map((t) => <FilaTurno key={t.id} turno={t} esAdmin={esAdmin} />)}
            {turnos?.length === 0 && <tr><td className="px-4 py-3 text-gray-400" colSpan={5}>No hay turnos todavía.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="mt-8 mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Ausencias</h2>
        {esAdmin && (
          <button onClick={() => setModalAusencia(true)} className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">
            <Plus size={16} /> Nueva ausencia
          </button>
        )}
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Empleado</th>
              <th className="px-4 py-2">Desde</th>
              <th className="px-4 py-2">Hasta</th>
              <th className="px-4 py-2">Motivo</th>
              <th className="px-4 py-2">Sustituto</th>
            </tr>
          </thead>
          <tbody>
            {ausencias?.map((a) => (
              <tr key={a.id} className="border-b border-gray-100">
                <td className="px-4 py-2">#{a.empleado}</td>
                <td className="px-4 py-2">{a.fecha_inicio}</td>
                <td className="px-4 py-2">{a.fecha_fin}</td>
                <td className="px-4 py-2">{a.motivo}</td>
                <td className="px-4 py-2">{a.sustituto ? `#${a.sustituto}` : '—'}</td>
              </tr>
            ))}
            {ausencias?.length === 0 && <tr><td className="px-4 py-3 text-gray-400" colSpan={5}>No hay ausencias registradas.</td></tr>}
          </tbody>
        </table>
      </div>

      {modalAusencia && (
        <ModalNuevaAusencia
          empleados={empleados}
          onClose={() => setModalAusencia(false)}
          onCreada={() => { setModalAusencia(false); qc.invalidateQueries({ queryKey: ['ausencias'] }); qc.invalidateQueries({ queryKey: ['turnos'] }) }}
        />
      )}
    </div>
  )
}
