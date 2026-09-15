// Modulos de dominio, todos sobre el mismo patron CRUD (ver rest() en client.js)
// mas las acciones puntuales de cada uno.
import client, { rest } from './client'

export const clientesApi = {
  ...rest('/clientes/'),
  exportarDatos: (id) => client.get(`/clientes/${id}/exportar-datos/`).then((r) => r.data),
  anonimizarDatos: (id) => client.delete(`/clientes/${id}/anonimizar-datos/`).then((r) => r.data),
}

export const serviciosApi = {
  ...rest('/servicios/'),
  desactivar: (id) => client.post(`/servicios/${id}/desactivar/`).then((r) => r.data),
  reordenar: (orden) => client.post('/servicios/reordenar/', { orden }).then((r) => r.data),
}

export const contratosApi = {
  ...rest('/contratos/'),
  anular: (id, data) => client.post(`/contratos/${id}/anular/`, data).then((r) => r.data),
  generarTurnos: (id) => client.post(`/contratos/${id}/generar-turnos/`).then((r) => r.data),
  subirPdfFirmado: (id, archivo) => {
    const form = new FormData()
    form.append('documento_pdf', archivo)
    return client.post(`/contratos/${id}/subir-pdf-firmado/`, form).then((r) => r.data)
  },
  // El endpoint de PDF exige el header Authorization (JWT): un <a href> comun
  // no lo manda, asi que se descarga con axios (que si lo agrega via el
  // interceptor de client.js) y se abre como blob.
  verPdf: async (id) => {
    const { data } = await client.get(`/contratos/${id}/pdf/`, { responseType: 'blob' })
    const url = URL.createObjectURL(data)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  },
}

export const ingresosApi = rest('/ingresos/')

export const empleadosApi = rest('/empleados/')

export const turnosApi = {
  ...rest('/turnos/'),
  registrarHoras: (id, horas_reales) =>
    client.post(`/turnos/${id}/registrar-horas-reales/`, { horas_reales }).then((r) => r.data),
}

export const ausenciasApi = rest('/ausencias/')

export const solicitudesApi = {
  ...rest('/solicitudes-ausencia/'),
  procesar: (id, data) => client.post(`/solicitudes-ausencia/${id}/procesar/`, data).then((r) => r.data),
}

export const facturasApi = {
  ...rest('/facturas/'),
  solicitarPendientes: (email_contador, cliente) =>
    client.post('/facturas/solicitar-pendientes/', { email_contador, cliente }).then((r) => r.data),
  subirPago: (id, archivo) => {
    const form = new FormData()
    form.append('comprobante_pago', archivo)
    return client.post(`/facturas/${id}/subir-pago/`, form).then((r) => r.data)
  },
  enviarContador: (id, email_contador) =>
    client.post(`/facturas/${id}/enviar-contador/`, { email_contador }).then((r) => r.data),
  enviarCliente: (id) => client.post(`/facturas/${id}/enviar-cliente/`).then((r) => r.data),
}

export const recibosApi = rest('/recibos/')
export const pagosEmpleadoApi = rest('/pagos-empleado/')

export const documentosApi = {
  obtenerPlantilla: () => client.get('/plantilla-clausulas/').then((r) => r.data),
  actualizarPlantilla: (data) => client.patch('/plantilla-clausulas/', data).then((r) => r.data),
}
