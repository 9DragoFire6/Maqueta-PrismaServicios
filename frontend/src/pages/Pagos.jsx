import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { mensajeError } from '../api/client'
import { pagosEmpleadoApi, recibosApi } from '../api/dominio'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

const formatoMoneda = (n) => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n || 0)

function ModalPagar({ recibo, onClose, onPagado }) {
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10))
  const [archivo, setArchivo] = useState(null)
  const [error, setError] = useState('')

  async function enviar(e) {
    e.preventDefault()
    try {
      const form = new FormData()
      form.append('recibo', recibo.id)
      form.append('fecha_pago', fecha)
      form.append('importe', recibo.importe)
      if (archivo) form.append('comprobante', archivo)
      await pagosEmpleadoApi.create(form)
      onPagado()
    } catch (err) {
      setError(mensajeError(err))
    }
  }

  return (
    <Modal titulo="Registrar pago" onClose={onClose} ancho="max-w-sm">
      <form onSubmit={enviar} className="space-y-3">
        <p className="text-sm text-gray-600">{recibo.concepto} — {formatoMoneda(recibo.importe)}</p>
        <input type="date" required value={fecha} onChange={(e) => setFecha(e.target.value)} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        <input type="file" onChange={(e) => setArchivo(e.target.files[0])} className="text-sm" />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancelar</button>
          <button type="submit" className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700">Registrar</button>
        </div>
      </form>
    </Modal>
  )
}

export default function Pagos() {
  const { esAdmin } = useAuth()
  const qc = useQueryClient()
  const { data: recibos, isLoading } = useQuery({ queryKey: ['recibos'], queryFn: () => recibosApi.list() })
  const [pagando, setPagando] = useState(null)

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-gray-800">{esAdmin ? 'Pagos a empleados' : 'Mis pagos'}</h1>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Concepto</th>
              {esAdmin && <th className="px-4 py-2">Empleado</th>}
              <th className="px-4 py-2">Fecha</th>
              <th className="px-4 py-2">Horas</th>
              <th className="px-4 py-2">Importe</th>
              <th className="px-4 py-2">Pagado</th>
              {esAdmin && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="px-4 py-3 text-gray-400" colSpan={6}>Cargando…</td></tr>}
            {recibos?.map((r) => (
              <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2">{r.concepto}</td>
                {esAdmin && <td className="px-4 py-2">#{r.empleado}</td>}
                <td className="px-4 py-2">{r.fecha}</td>
                <td className="px-4 py-2">{r.horas}</td>
                <td className="px-4 py-2">{formatoMoneda(r.importe)}</td>
                <td className="px-4 py-2">{r.pago ? 'Sí' : 'No'}</td>
                {esAdmin && (
                  <td className="px-4 py-2 text-right">
                    {!r.pago && <button onClick={() => setPagando(r)} className="text-green-700 hover:underline">Registrar pago</button>}
                  </td>
                )}
              </tr>
            ))}
            {recibos?.length === 0 && <tr><td className="px-4 py-3 text-gray-400" colSpan={6}>No hay recibos todavía.</td></tr>}
          </tbody>
        </table>
      </div>

      {pagando && (
        <ModalPagar recibo={pagando} onClose={() => setPagando(null)} onPagado={() => { setPagando(null); qc.invalidateQueries({ queryKey: ['recibos'] }) }} />
      )}
    </div>
  )
}
