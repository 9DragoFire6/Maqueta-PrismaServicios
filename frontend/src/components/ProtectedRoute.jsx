import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ soloAdmin = false }) {
  const { usuario } = useAuth()

  if (!usuario) return <Navigate to="/login" replace />
  if (soloAdmin && usuario.rol !== 'admin') return <Navigate to="/" replace />

  return <Outlet />
}
