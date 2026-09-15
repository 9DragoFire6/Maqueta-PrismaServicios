import { useQuery } from '@tanstack/react-query'
import { authApi } from '../api/auth'
import { useAuth } from '../context/AuthContext'

function Tarjeta({ etiqueta, valor }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-sm text-gray-500">{etiqueta}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-800">{valor}</p>
    </div>
  )
}

const formatoMoneda = (n) => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n || 0)

export default function Dashboard() {
  const { usuario, esAdmin } = useAuth()
  const { data: stats } = useQuery({ queryKey: ['dashboard-stats'], queryFn: authApi.dashboardStats })
  const { data: mensual } = useQuery({
    queryKey: ['dashboard-mensual'],
    queryFn: authApi.dashboardMensual,
    enabled: esAdmin,
  })

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold text-gray-800">Hola, {usuario?.first_name || usuario?.username}</h1>
      <p className="mb-6 text-sm text-gray-500">Resumen general.</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {esAdmin ? (
          <>
            <Tarjeta etiqueta="Clientes activos" valor={stats?.clientes_activos ?? '—'} />
            <Tarjeta etiqueta="Cobros pendientes" valor={formatoMoneda(stats?.cobros_pendientes)} />
            <Tarjeta etiqueta="Pagos a empleados pendientes" valor={formatoMoneda(stats?.pagos_pendientes)} />
          </>
        ) : (
          <Tarjeta etiqueta="Mis pagos pendientes" valor={formatoMoneda(stats?.mis_pagos_pendientes)} />
        )}
      </div>

      {esAdmin && mensual && (
        <div className="mt-8 rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-medium text-gray-600">Facturación y pagos, últimos 6 meses</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-gray-500">
                  <th className="py-2 pr-4">Mes</th>
                  <th className="py-2 pr-4">Facturación</th>
                  <th className="py-2 pr-4">Pagos a empleados</th>
                </tr>
              </thead>
              <tbody>
                {mensual.map((m) => (
                  <tr key={m.mes} className="border-b border-gray-100">
                    <td className="py-2 pr-4">{m.mes}</td>
                    <td className="py-2 pr-4">{formatoMoneda(m.facturacion)}</td>
                    <td className="py-2 pr-4">{formatoMoneda(m.pagos_empleados)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
