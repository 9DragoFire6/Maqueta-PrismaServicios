import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { mensajeError } from '../api/client'
import { facturasApi } from '../api/dominio'
import Modal from '../components/Modal'

const ESTADO_LABEL = { pendiente: 'Pendiente', cobrada: 'Cobrada', vencida: 'Vencida', anulada: 'Anulada' }
const formatoMoneda = (n) => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n || 0)

function ModalSolicitarPendientes({ onClose, onEnviado }) {
  const [email, setEmail] = useState('')
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    setError('')
    try {
      const r = await facturasApi.solicitarPendientes(email)
      setResultado(r)
      onEnviado()
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <Modal titulo="Solicitar facturas pendientes" onClose={onClose} ancho="max-w-sm">
      {resultado ? (
        <div className="space-y-2 text-sm">
          <p className="text-green-700">Enviadas: {resultado.enviadas.join(', ') || 'ninguna'}</p>
          {resultado.errores.length > 0 && <p className="text-red-600">Errores: {JSON.stringify(resultado.errores)}</p>}
          <button onClick={onClose} className="mt-2 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Cerrar</button>
        </div>
      ) : (
        <form onSubmit={enviar} className="space-y-3">
          <p className="text-sm text-gray-500">
            Agrupa los ingresos sin facturar por contrato y le manda un correo al contador (sin proveedor real: se imprime en la consola del backend).
          </p>
          <input type="email" required placeholder="Email del contador" value={email} onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
            <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Enviar</button>
          </div>
        </form>
      )}
    </Modal>
  )
}

function ModalCompletar({ factura, onClose, onListo }) {
  const [numero, setNumero] = useState(factura.numero || '')
  const [fechaEmision, setFechaEmision] = useState(factura.fecha_emision || '')
  const [fechaVencimiento, setFechaVencimiento] = useState(factura.fecha_vencimiento || '')
  const [archivo, setArchivo] = useState(null)
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    try {
      await facturasApi.update(factura.id, {
        numero, fecha_emision: fechaEmision || null, fecha_vencimiento: fechaVencimiento || null,
      })
      if (archivo) {
        const form = new FormData()
        form.append('archivo_pdf', archivo)
        await facturasApi.update(factura.id, form)
      }
      onListo()
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <Modal titulo="Completar factura" onClose={onClose} ancho="max-w-sm">
      <form onSubmit={enviar} className="space-y-3">
        <input placeholder="Número real (del contador)" value={numero} onChange={(e) => setNumero(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        <div className="grid grid-cols-2 gap-2">
          <input type="date" value={fechaEmision} onChange={(e) => setFechaEmision(e.target.value)} className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
          <input type="date" value={fechaVencimiento} onChange={(e) => setFechaVencimiento(e.target.value)} className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
        </div>
        <input type="file" accept="application/pdf" onChange={(e) => setArchivo(e.target.files[0])} className="text-sm" />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
          <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Guardar</button>
        </div>
      </form>
    </Modal>
  )
}

export default function Facturas() {
  const qc = useQueryClient()
  const { data: facturas, isLoading } = useQuery({ queryKey: ['facturas'], queryFn: () => facturasApi.list() })
  const [modalPendientes, setModalPendientes] = useState(false)
  const [completando, setCompletando] = useState(null)

  const invalidar = () => qc.invalidateQueries({ queryKey: ['facturas'] })

  const subirPago = useMutation({
    mutationFn: ({ id, archivo }) => facturasApi.subirPago(id, archivo),
    onSuccess: invalidar,
    onError: (err) => alert(mensajeError(err)),
  })

  async function enviarContador(f) {
    const email = prompt('Email del contador para reenviar:')
    if (!email) return
    await facturasApi.enviarContador(f.id, email)
    alert('Enviado (revisá la consola del backend).')
  }

  async function enviarCliente(f) {
    await facturasApi.enviarCliente(f.id)
    alert('Enviado (revisá la consola del backend).')
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Facturas</h1>
        <button onClick={() => setModalPendientes(true)} className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">
          Solicitar pendientes al contador
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Número</th>
              <th className="px-4 py-2">Cliente</th>
              <th className="px-4 py-2">Importe</th>
              <th className="px-4 py-2">Estado</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="px-4 py-3 text-gray-400" colSpan={5}>Cargando…</td></tr>}
            {facturas?.map((f) => (
              <tr key={f.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2">{f.numero || 'Sin responder'}</td>
                <td className="px-4 py-2">#{f.cliente}</td>
                <td className="px-4 py-2">{formatoMoneda(f.importe)}</td>
                <td className="px-4 py-2">{ESTADO_LABEL[f.estado]}</td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => setCompletando(f)} className="mr-3 text-slate-600 hover:underline">Completar</button>
                  <button onClick={() => enviarContador(f)} className="mr-3 text-slate-600 hover:underline">Reenviar contador</button>
                  {f.numero && f.estado === 'pendiente' && (
                    <>
                      <button onClick={() => enviarCliente(f)} className="mr-3 text-slate-600 hover:underline">Enviar a cliente</button>
                      <label className="cursor-pointer text-green-700 hover:underline">
                        Subir pago
                        <input type="file" className="hidden" onChange={(e) => e.target.files[0] && subirPago.mutate({ id: f.id, archivo: e.target.files[0] })} />
                      </label>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {facturas?.length === 0 && <tr><td className="px-4 py-3 text-gray-400" colSpan={5}>No hay facturas todavía.</td></tr>}
          </tbody>
        </table>
      </div>

      {modalPendientes && <ModalSolicitarPendientes onClose={() => setModalPendientes(false)} onEnviado={invalidar} />}
      {completando && <ModalCompletar factura={completando} onClose={() => setCompletando(null)} onListo={() => { setCompletando(null); invalidar() }} />}
    </div>
  )
}
