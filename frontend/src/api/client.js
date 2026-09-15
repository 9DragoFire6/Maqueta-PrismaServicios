import axios from 'axios'

export const API_BASE_URL = 'http://localhost:8000/api'

const client = axios.create({ baseURL: API_BASE_URL })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refrescando = null

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const refresh = localStorage.getItem('refresh')
    if (error.response?.status === 401 && refresh && !original._retry && !original.url.includes('/auth/')) {
      original._retry = true
      try {
        if (!refrescando) {
          refrescando = axios
            .post(`${API_BASE_URL}/auth/refresh/`, { refresh })
            .finally(() => { refrescando = null })
        }
        const { data } = await refrescando
        localStorage.setItem('access', data.access)
        original.headers.Authorization = `Bearer ${data.access}`
        return client(original)
      } catch (e) {
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
        localStorage.removeItem('usuario')
        window.location.href = '/login'
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  },
)

export default client

/** Fábrica de métodos CRUD estándar sobre un endpoint tipo router DRF. */
export function rest(base) {
  return {
    list: (params) => client.get(base, { params }).then((r) => r.data),
    get: (id) => client.get(`${base}${id}/`).then((r) => r.data),
    create: (data) => client.post(base, data).then((r) => r.data),
    update: (id, data) => client.patch(`${base}${id}/`, data).then((r) => r.data),
    remove: (id) => client.delete(`${base}${id}/`).then((r) => r.data),
  }
}

/** Extrae un mensaje de error legible de una respuesta de la API. */
export function mensajeError(error) {
  const data = error?.response?.data
  if (!data) return error?.message || 'Ocurrió un error inesperado.'
  if (typeof data === 'string') return data
  if (data.error) return typeof data.error === 'string' ? data.error : JSON.stringify(data.error)
  if (data.detail) return data.detail
  const primeraClave = Object.keys(data)[0]
  if (primeraClave) {
    const valor = data[primeraClave]
    return Array.isArray(valor) ? valor[0] : String(valor)
  }
  return 'Ocurrió un error inesperado.'
}
