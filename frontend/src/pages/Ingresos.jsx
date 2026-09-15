import { useQuery } from '@tanstack/react-query'
import { ingresosApi } from '../api/dominio'

const ESTADO_LABEL = { pendiente: 'Pendiente', facturado: 'Facturado', pagado: 'Pagado' }
const formatoMoneda = (n) => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n || 0)

export default function Ingresos() {
  const { data: ingresos, isLoading } = useQuery({ queryKey: ['ingresos'], queryFn: () => ingresosApi.list() })

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-gray-800">Ingresos</h1>
      <p className="mb-4 text-sm text-gray-500">
        Se generan solos a partir de las horas reales trabajadas, agrupadas por semana (lunes a domingo).
      </p>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
              <th className="px-4 py-2">Semana</th>
              <th className="px-4 py-2">Cliente</th>
              <th className="px-4 py-2">Servicio</th>
              <th className="px-4 py-2">Horas</th>
              <th className="px-4 py-2">Base</th>
              <th className="px-4 py-2">IVA</th>
              <th className="px-4 py-2">Cobrado</th>
              <th className="px-4 py-2">Pago empleado</th>
              <th className="px-4 py-2">Estado</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td className="px-4 py-3 text-gray-400" colSpan={9}>Cargando…</td></tr>}
            {ingresos?.map((i) => (
              <tr key={i.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2">{i.fecha} — {i.periodo_fin}</td>
                <td className="px-4 py-2">#{i.cliente}</td>
                <td className="px-4 py-2">#{i.servicio}</td>
                <td className="px-4 py-2">{i.horas}</td>
                <td className="px-4 py-2">{formatoMoneda(i.base_real)}</td>
                <td className="px-4 py-2">{formatoMoneda(i.iva_monto)}</td>
                <td className="px-4 py-2 font-medium">{formatoMoneda(i.cobrado)}</td>
                <td className="px-4 py-2">{formatoMoneda(i.pago_empleado)}</td>
                <td className="px-4 py-2">{ESTADO_LABEL[i.estado]}</td>
              </tr>
            ))}
            {ingresos?.length === 0 && <tr><td className="px-4 py-3 text-gray-400" colSpan={9}>No hay ingresos todavía (se generan al registrar horas reales trabajadas).</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
