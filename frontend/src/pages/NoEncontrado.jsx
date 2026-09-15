import { Link } from 'react-router-dom'

export default function NoEncontrado() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-gray-50 text-center">
      <h1 className="text-3xl font-semibold text-gray-800">404</h1>
      <p className="text-gray-500">Esta página no existe.</p>
      <Link to="/" className="text-sm text-slate-700 underline">
        Volver al inicio
      </Link>
    </div>
  )
}
