import { useEffect, useState } from 'react'
import { documentosApi } from '../api/dominio'
import { mensajeError } from '../api/client'
import DobleVerificacionModal from '../components/DobleVerificacionModal'

export default function PlantillaClausulas() {
  const [contenido, setContenido] = useState('')
  const [meta, setMeta] = useState(null)
  const [pedirVerificacion, setPedirVerificacion] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    documentosApi.obtenerPlantilla().then((r) => { setContenido(r.contenido); setMeta(r) })
  }, [])

  async function guardar(datosVerificacion) {
    setError('')
    try {
      const r = await documentosApi.actualizarPlantilla({ contenido, ...datosVerificacion })
      setMeta(r)
      setMensaje('Plantilla actualizada.')
      setPedirVerificacion(false)
    } catch (err) {
      setError(mensajeError(err))
      setPedirVerificacion(false)
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold text-gray-800">Plantilla de contrato</h1>
      <p className="mb-4 text-sm text-gray-500">
        Cláusulas legales (secciones 2 en adelante) que se imprimen en el PDF del contrato. La Sección 1
        (servicios contratados) se arma sola. Formato: <code>## </code> para un título de sección, líneas con{' '}
        <code>- </code> para listas, <code>**texto**</code> para negrita.
      </p>
      {meta?.actualizado_por && (
        <p className="mb-4 text-xs text-gray-400">Última edición: {meta.actualizado_por}, {new Date(meta.actualizado_en).toLocaleString()}</p>
      )}
      <textarea
        value={contenido}
        onChange={(e) => setContenido(e.target.value)}
        rows={22}
        className="w-full rounded border border-gray-300 p-3 font-mono text-xs focus:border-slate-500 focus:outline-none"
      />
      {mensaje && <p className="mt-2 text-sm text-green-700">{mensaje}</p>}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <button
        onClick={() => setPedirVerificacion(true)}
        className="mt-3 rounded bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700"
      >
        Guardar cambios
      </button>

      {pedirVerificacion && <DobleVerificacionModal onClose={() => setPedirVerificacion(false)} onConfirmado={guardar} />}
    </div>
  )
}
