import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { mensajeError } from '../api/client'
import { clientesApi, contratosApi, empleadosApi, serviciosApi } from '../api/dominio'
import DobleVerificacionModal from '../components/DobleVerificacionModal'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

const DIAS = [
  ['lun', 'L'], ['mar', 'M'], ['mie', 'X'], ['jue', 'J'], ['vie', 'V'], ['sab', 'S'], ['dom', 'D'],
]

const ACUERDO_VACIO = {
  servicio: '', profesional: '', dias_semana: [], hora_inicio: '', hora_fin: '',
  horas_estimadas: '', tarifa_manual: '', fecha_inicio: '', duracion_semanas: 4,
}

function FilaAcuerdo({ acuerdo, servicios, empleados, onCambiar, onQuitar }) {
  function toggleDia(dia) {
    const dias = acuerdo.dias_semana.includes(dia)
      ? acuerdo.dias_semana.filter((d) => d !== dia)
      : [...acuerdo.dias_semana, dia]
    onCambiar({ ...acuerdo, dias_semana: dias })
  }

  return (
    <div className="mb-3 rounded border border-gray-200 p-3">
      <div className="mb-2 grid grid-cols-2 gap-2">
        <select required value={acuerdo.servicio} onChange={(e) => onCambiar({ ...acuerdo, servicio: e.target.value })}
          className="rounded border border-gray-300 px-2 py-1.5 text-sm">
          <option value="">Servicio…</option>
          {servicios?.map((s) => <option key={s.id} value={s.id}>{s.codigo} — {s.nombre}</option>)}
        </select>
        <select required value={acuerdo.profesional} onChange={(e) => onCambiar({ ...acuerdo, profesional: e.target.value })}
          className="rounded border border-gray-300 px-2 py-1.5 text-sm">
          <option value="">Empleado…</option>
          {empleados?.map((e) => <option key={e.id} value={e.id}>{e.nombre} {e.apellido}</option>)}
        </select>
      </div>
      <div className="mb-2 flex items-center gap-1.5">
        {DIAS.map(([valor, letra]) => (
          <button type="button" key={valor} onClick={() => toggleDia(valor)}
            className={`h-7 w-7 rounded text-xs font-medium ${acuerdo.dias_semana.includes(valor) ? 'bg-slate-800 text-white' : 'bg-gray-100 text-gray-500'}`}>
            {letra}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-2">
        <input type="time" value={acuerdo.hora_inicio} onChange={(e) => onCambiar({ ...acuerdo, hora_inicio: e.target.value })}
          className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
        <input type="time" value={acuerdo.hora_fin} onChange={(e) => onCambiar({ ...acuerdo, hora_fin: e.target.value })}
          className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
        <input type="date" required value={acuerdo.fecha_inicio} onChange={(e) => onCambiar({ ...acuerdo, fecha_inicio: e.target.value })}
          className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
        <input type="number" min={4} value={acuerdo.duracion_semanas} placeholder="Semanas (mín. 4)"
          onChange={(e) => onCambiar({ ...acuerdo, duracion_semanas: e.target.value })}
          className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
      </div>
      <div className="mt-2 flex items-center justify-between">
        <input type="number" step="0.01" placeholder="Tarifa manual (opcional)" value={acuerdo.tarifa_manual}
          onChange={(e) => onCambiar({ ...acuerdo, tarifa_manual: e.target.value })}
          className="w-48 rounded border border-gray-300 px-2 py-1.5 text-sm" />
        <button type="button" onClick={onQuitar} className="text-red-500 hover:text-red-700"><Trash2 size={16} /></button>
      </div>
    </div>
  )
}

function FormularioContrato({ inicial, clientes, servicios, empleados, onListo, onCancelar, esEdicion }) {
  const [clienteId, setClienteId] = useState(inicial.cliente || '')
  const [observaciones, setObservaciones] = useState(inicial.observaciones || '')
  const [acuerdos, setAcuerdos] = useState(inicial.acuerdos?.length ? inicial.acuerdos : [ACUERDO_VACIO])
  const [pedirVerificacion, setPedirVerificacion] = useState(false)

  function armarForm() {
    return { cliente: clienteId, observaciones, acuerdos: acuerdos.map((a) => ({ ...a, id: a.id })) }
  }

  return (
    <>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (esEdicion) setPedirVerificacion(true)
          else onListo(armarForm())
        }}
        className="space-y-3"
      >
        <div>
          <label className="mb-1 block text-sm text-gray-600">Cliente</label>
          <select required value={clienteId} onChange={(e) => setClienteId(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
            <option value="">Seleccionar…</option>
            {clientes?.map((c) => <option key={c.id} value={c.id}>{c.nombre_contacto}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-2 block text-sm text-gray-600">Servicios contratados</label>
          {acuerdos.map((a, i) => (
            <FilaAcuerdo
              key={i}
              acuerdo={a}
              servicios={servicios}
              empleados={empleados}
              onCambiar={(nuevo) => setAcuerdos(acuerdos.map((x, j) => (j === i ? nuevo : x)))}
              onQuitar={() => setAcuerdos(acuerdos.filter((_, j) => j !== i))}
            />
          ))}
          <button type="button" onClick={() => setAcuerdos([...acuerdos, ACUERDO_VACIO])}
            className="flex items-center gap-1 text-sm text-slate-600 hover:underline">
            <Plus size={14} /> Agregar servicio
          </button>
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">Observaciones</label>
          <textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm" rows={2} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onCancelar} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
          <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Guardar</button>
        </div>
      </form>
      {pedirVerificacion && (
        <DobleVerificacionModal onClose={() => setPedirVerificacion(false)} onConfirmado={(v) => onListo({ ...armarForm(), ...v })} />
      )}
    </>
  )
}

function ModalAnular({ contrato, onClose, onAnulado }) {
  const [motivo, setMotivo] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    try {
      await contratosApi.anular(contrato.id, { motivo, fecha_inicio_anulacion: desde, fecha_fin_anulacion: hasta })
      onAnulado()
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <Modal titulo="Anular contrato" onClose={onClose} ancho="max-w-sm">
      <form onSubmit={enviar} className="space-y-3">
        <textarea required placeholder="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm" rows={2} />
        <div className="grid grid-cols-2 gap-2">
          <input type="date" required value={desde} onChange={(e) => setDesde(e.target.value)} className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
          <input type="date" required value={hasta} onChange={(e) => setHasta(e.target.value)} className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
          <button type="submit" className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700">Anular</button>
        </div>
      </form>
    </Modal>
  )
}

export default function Contratos() {
  const { esAdmin } = useAuth()
  const qc = useQueryClient()
  const { data: contratos, isLoading } = useQuery({ queryKey: ['contratos'], queryFn: () => contratosApi.list() })
  const { data: clientes } = useQuery({ queryKey: ['clientes'], queryFn: () => clientesApi.list(), enabled: esAdmin })
  const { data: servicios } = useQuery({ queryKey: ['servicios'], queryFn: () => serviciosApi.list(), enabled: esAdmin })
  const { data: empleados } = useQuery({ queryKey: ['empleados'], queryFn: () => empleadosApi.list() })
  const [modal, setModal] = useState(null)
  const [anulando, setAnulando] = useState(null)
  const [error, setError] = useState('')

  const invalidar = () => qc.invalidateQueries({ queryKey: ['contratos'] })

  const guardar = useMutation({
    mutationFn: (form) => (modal?.id ? contratosApi.update(modal.id, form) : contratosApi.create(form)),
    onSuccess: () => { invalidar(); setModal(null); setError('') },
    onError: (err) => setError(mensajeError(err)),
  })

  async function activar(contrato) {
    if (!confirm('¿Activar este contrato?')) return
    await contratosApi.update(contrato.id, { estado: 'activo' })
    invalidar()
  }

  async function eliminar(contrato) {
    if (!confirm('¿Eliminar este contrato en borrador?')) return
    await contratosApi.remove(contrato.id)
    invalidar()
  }

  async function generarTurnos(contrato) {
    const r = await contratosApi.generarTurnos(contrato.id)
    alert(`Turnos: ${r.creados} creados, ${r.actualizados} actualizados, ${r.ya_al_dia} ya al día.`)
  }

  async function subirFirmado(contrato, archivo) {
    await contratosApi.subirPdfFirmado(contrato.id, archivo)
    invalidar()
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">{esAdmin ? 'Contratos' : 'Mis contratos'}</h1>
        {esAdmin && (
          <button onClick={() => { setModal('crear'); setError('') }} className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">
            <Plus size={16} /> Nuevo contrato
          </button>
        )}
      </div>

      <div className="space-y-3">
        {isLoading && <p className="text-sm text-gray-400">Cargando…</p>}
        {contratos?.map((c) => (
          <div key={c.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="mb-2 flex items-center justify-between">
              <div>
                <span className="font-medium text-gray-800">{c.cliente_nombre || `Cliente #${c.cliente}`}</span>
                <span className={`ml-3 rounded px-2 py-0.5 text-xs font-medium ${
                  { borrador: 'bg-gray-100 text-gray-600', activo: 'bg-green-100 text-green-700', finalizado: 'bg-blue-100 text-blue-700', anulado: 'bg-red-100 text-red-700' }[c.estado]
                }`}>{c.estado}</span>
              </div>
              <span className="text-xs text-gray-400">{c.fecha_inicio} — {c.fecha_fin || '…'}</span>
            </div>
            <ul className="mb-3 space-y-1 text-sm text-gray-600">
              {c.acuerdos?.map((a) => (
                <li key={a.id}>
                  {a.servicio_nombre} · {a.profesional_nombre} · {a.dias_semana?.join(', ')}
                  {a.hora_inicio && ` · ${a.hora_inicio.slice(0, 5)}–${a.hora_fin?.slice(0, 5)}`}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-3 text-sm">
              <button onClick={() => contratosApi.verPdf(c.id)} className="text-slate-600 hover:underline">Ver PDF</button>
              {esAdmin && c.estado === 'borrador' && (
                <>
                  <button onClick={() => { setModal(c); setError('') }} className="text-slate-600 hover:underline">Editar</button>
                  <button onClick={() => activar(c)} className="text-green-700 hover:underline">Activar</button>
                  <button onClick={() => eliminar(c)} className="text-red-600 hover:underline">Eliminar</button>
                </>
              )}
              {esAdmin && c.estado === 'activo' && (
                <button onClick={() => setAnulando(c)} className="text-red-600 hover:underline">Anular</button>
              )}
              {esAdmin && (
                <>
                  <button onClick={() => generarTurnos(c)} className="text-slate-600 hover:underline">Generar turnos</button>
                  <label className="cursor-pointer text-slate-600 hover:underline">
                    Subir firmado
                    <input type="file" accept="application/pdf" className="hidden" onChange={(e) => e.target.files[0] && subirFirmado(c, e.target.files[0])} />
                  </label>
                  {c.documento_pdf && <a href={c.documento_pdf} target="_blank" rel="noreferrer" className="text-slate-600 hover:underline">Ver firmado</a>}
                </>
              )}
            </div>
          </div>
        ))}
        {contratos?.length === 0 && <p className="text-sm text-gray-400">No hay contratos todavía.</p>}
      </div>

      {modal && (
        <Modal titulo={modal === 'crear' ? 'Nuevo contrato' : 'Editar contrato'} onClose={() => setModal(null)} ancho="max-w-2xl">
          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          <FormularioContrato
            inicial={modal === 'crear' ? { cliente: '', observaciones: '', acuerdos: [] } : modal}
            clientes={clientes}
            servicios={servicios}
            empleados={empleados}
            esEdicion={modal !== 'crear'}
            onListo={(form) => guardar.mutate(form)}
            onCancelar={() => setModal(null)}
          />
        </Modal>
      )}

      {anulando && <ModalAnular contrato={anulando} onClose={() => setAnulando(null)} onAnulado={() => { setAnulando(null); invalidar() }} />}
    </div>
  )
}
