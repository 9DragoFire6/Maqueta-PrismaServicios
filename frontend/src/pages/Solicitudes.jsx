import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { mensajeError } from '../api/client'
import { ausenciasApi, solicitudesApi, turnosApi } from '../api/dominio'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

const TIPOS = {
  mal_ingresada: 'Ausencia mal ingresada',
  permiso: 'Permiso de ausencia',
  correccion_horas: 'Corrección de horas trabajadas',
  reasignacion_extendida: 'Reasignación extendida',
}

function ModalNuevaSolicitud({ ausencias, turnos, onClose, onCreada }) {
  const [tipo, setTipo] = useState('mal_ingresada')
  const [ausencia, setAusencia] = useState('')
  const [turno, setTurno] = useState('')
  const [motivo, setMotivo] = useState('')
  const [tituloPermiso, setTituloPermiso] = useState('')
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    const payload = { tipo, motivo }
    if (tipo === 'correccion_horas') payload.turno = turno
    else payload.ausencia = ausencia
    if (tipo === 'permiso') payload.titulo_permiso = tituloPermiso
    try {
      await solicitudesApi.create(payload)
      onCreada()
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <Modal titulo="Nueva solicitud" onClose={onClose} ancho="max-w-sm">
      <form onSubmit={enviar} className="space-y-3">
        <select value={tipo} onChange={(e) => setTipo(e.target.value)} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
          <option value="mal_ingresada">{TIPOS.mal_ingresada}</option>
          <option value="permiso">{TIPOS.permiso}</option>
          <option value="correccion_horas">{TIPOS.correccion_horas}</option>
        </select>

        {tipo === 'correccion_horas' ? (
          <select required value={turno} onChange={(e) => setTurno(e.target.value)} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
            <option value="">Turno a corregir…</option>
            {turnos?.map((t) => <option key={t.id} value={t.id}>{t.fecha} — {t.horas_reales ?? 'sin horas'}h</option>)}
          </select>
        ) : (
          <select required value={ausencia} onChange={(e) => setAusencia(e.target.value)} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
            <option value="">Ausencia relacionada…</option>
            {ausencias?.map((a) => <option key={a.id} value={a.id}>{a.fecha_inicio} — {a.motivo}</option>)}
          </select>
        )}

        {tipo === 'permiso' && (
          <input placeholder="Título del permiso" value={tituloPermiso} onChange={(e) => setTituloPermiso(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        )}

        <textarea required placeholder="Motivo / detalle" value={motivo} onChange={(e) => setMotivo(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm" rows={2} />

        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
          <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Enviar</button>
        </div>
      </form>
    </Modal>
  )
}

function ModalProcesar({ solicitud, onClose, onProcesada }) {
  const [resolucion, setResolucion] = useState('aceptada')
  const [nota, setNota] = useState('')
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    try {
      await solicitudesApi.procesar(solicitud.id, { resolucion, nota_resolucion: nota })
      onProcesada()
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <Modal titulo="Procesar solicitud" onClose={onClose} ancho="max-w-sm">
      <form onSubmit={enviar} className="space-y-3">
        <p className="text-sm text-gray-600">{TIPOS[solicitud.tipo]} — {solicitud.motivo}</p>
        <select value={resolucion} onChange={(e) => setResolucion(e.target.value)} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
          <option value="aceptada">Aceptada tal cual</option>
          <option value="rechazada">Rechazada</option>
          <option value="corregida">Corregida con otro valor</option>
        </select>
        <textarea placeholder="Nota (opcional)" value={nota} onChange={(e) => setNota(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm" rows={2} />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
          <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Confirmar</button>
        </div>
      </form>
    </Modal>
  )
}

export default function Solicitudes() {
  const { esAdmin } = useAuth()
  const qc = useQueryClient()
  const { data: solicitudes, isLoading } = useQuery({ queryKey: ['solicitudes'], queryFn: () => solicitudesApi.list() })
  const { data: ausencias } = useQuery({ queryKey: ['ausencias'], queryFn: () => ausenciasApi.list() })
  const { data: turnos } = useQuery({ queryKey: ['turnos'], queryFn: () => turnosApi.list() })
  const [modalNueva, setModalNueva] = useState(false)
  const [procesando, setProcesando] = useState(null)

  const invalidar = () => qc.invalidateQueries({ queryKey: ['solicitudes'] })

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">{esAdmin ? 'Solicitudes de corrección' : 'Mis solicitudes'}</h1>
        <button onClick={() => setModalNueva(true)} className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">
          <Plus size={16} /> Nueva solicitud
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Tipo</th>
              <th className="px-4 py-2">Motivo</th>
              <th className="px-4 py-2">Estado</th>
              <th className="px-4 py-2">Resolución</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="px-4 py-3 text-gray-400" colSpan={5}>Cargando…</td></tr>}
            {solicitudes?.map((s) => (
              <tr key={s.id} className="border-b border-gray-100">
                <td className="px-4 py-2">{TIPOS[s.tipo] || s.tipo}</td>
                <td className="px-4 py-2">{s.motivo}</td>
                <td className="px-4 py-2">{s.estado === 'pendiente' ? 'Pendiente' : 'Procesada'}</td>
                <td className="px-4 py-2">{s.resolucion || '—'}</td>
                <td className="px-4 py-2 text-right">
                  {esAdmin && s.estado === 'pendiente' && (
                    <button onClick={() => setProcesando(s)} className="text-slate-600 hover:underline">Procesar</button>
                  )}
                </td>
              </tr>
            ))}
            {solicitudes?.length === 0 && <tr><td className="px-4 py-3 text-gray-400" colSpan={5}>No hay solicitudes todavía.</td></tr>}
          </tbody>
        </table>
      </div>

      {modalNueva && (
        <ModalNuevaSolicitud ausencias={ausencias} turnos={turnos} onClose={() => setModalNueva(false)} onCreada={() => { setModalNueva(false); invalidar() }} />
      )}
      {procesando && (
        <ModalProcesar solicitud={procesando} onClose={() => setProcesando(null)} onProcesada={() => { setProcesando(null); invalidar() }} />
      )}
    </div>
  )
}
