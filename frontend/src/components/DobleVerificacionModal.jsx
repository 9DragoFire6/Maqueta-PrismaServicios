import { useEffect, useState } from 'react'
import { authApi } from '../api/auth'
import { mensajeError } from '../api/client'
import Modal from './Modal'

/**
 * Reconfirma la identidad antes de una accion sensible (editar un contrato,
 * la plantilla de clausulas, etc.) -- pide contraseña o codigo de 2FA segun
 * lo que tenga activado quien esta logueado. Al confirmar, entrega al padre
 * los mismos datos que hay que mandar en el request real (el backend vuelve
 * a validarlos del lado del servidor, esto no crea ninguna sesion elevada).
 */
export default function DobleVerificacionModal({ onClose, onConfirmado }) {
  const [usa2fa, setUsa2fa] = useState(null)
  const [valor, setValor] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    authApi.estado2fa().then((r) => setUsa2fa(r.activo)).catch(() => setUsa2fa(false))
  }, [])

  async function confirmar(e) {
    e.preventDefault()
    setEnviando(true)
    setError('')
    const datos = usa2fa ? { codigo: valor } : { password: valor }
    try {
      await authApi.verificarPassword(datos)
      onConfirmado(datos)
    } catch (err) {
      setError(mensajeError(err))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal titulo="Confirmá tu identidad" onClose={onClose} ancho="max-w-sm">
      <form onSubmit={confirmar} className="space-y-4">
        <p className="text-sm text-gray-500">
          Esta es una acción sensible. {usa2fa ? 'Ingresá el código de tu app de autenticación.' : 'Volvé a ingresar tu contraseña.'}
        </p>
        <input
          type={usa2fa ? 'text' : 'password'}
          autoFocus
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          placeholder={usa2fa ? 'Código de 6 dígitos' : 'Contraseña'}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">
            Cancelar
          </button>
          <button
            type="submit"
            disabled={enviando || !valor || usa2fa === null}
            className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
          >
            Confirmar
          </button>
        </div>
      </form>
    </Modal>
  )
}
