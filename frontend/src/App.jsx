import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './context/AuthContext'
import Clientes from './pages/Clientes'
import Contratos from './pages/Contratos'
import Dashboard from './pages/Dashboard'
import Empleados from './pages/Empleados'
import Facturas from './pages/Facturas'
import Ingresos from './pages/Ingresos'
import Login from './pages/Login'
import NoEncontrado from './pages/NoEncontrado'
import Pagos from './pages/Pagos'
import Perfil from './pages/Perfil'
import PlantillaClausulas from './pages/PlantillaClausulas'
import RecuperarPassword from './pages/RecuperarPassword'
import RestablecerPassword from './pages/RestablecerPassword'
import Servicios from './pages/Servicios'
import Solicitudes from './pages/Solicitudes'
import Turnos from './pages/Turnos'
import Usuarios from './pages/Usuarios'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/recuperar-password" element={<RecuperarPassword />} />
            <Route path="/restablecer-password/:uid/:token" element={<RestablecerPassword />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/contratos" element={<Contratos />} />
                <Route path="/empleados" element={<Empleados />} />
                <Route path="/turnos" element={<Turnos />} />
                <Route path="/solicitudes" element={<Solicitudes />} />
                <Route path="/pagos" element={<Pagos />} />
                <Route path="/perfil" element={<Perfil />} />

                <Route element={<ProtectedRoute soloAdmin />}>
                  <Route path="/clientes" element={<Clientes />} />
                  <Route path="/servicios" element={<Servicios />} />
                  <Route path="/ingresos" element={<Ingresos />} />
                  <Route path="/facturas" element={<Facturas />} />
                  <Route path="/usuarios" element={<Usuarios />} />
                  <Route path="/plantilla-clausulas" element={<PlantillaClausulas />} />
                </Route>
              </Route>
            </Route>

            <Route path="/404" element={<NoEncontrado />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
