import {
  Banknote,
  CalendarClock,
  ClipboardList,
  FileSignature,
  FileText,
  LayoutDashboard,
  LogOut,
  Receipt,
  ScrollText,
  Settings,
  UserCircle,
  Users,
  Wrench,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ADMIN = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, fin: true },
  { to: '/clientes', label: 'Clientes', icon: Users },
  { to: '/servicios', label: 'Servicios', icon: Wrench },
  { to: '/contratos', label: 'Contratos', icon: FileSignature },
  { to: '/empleados', label: 'Empleados', icon: UserCircle },
  { to: '/turnos', label: 'Turnos', icon: CalendarClock },
  { to: '/solicitudes', label: 'Solicitudes', icon: ClipboardList },
  { to: '/ingresos', label: 'Ingresos', icon: Receipt },
  { to: '/facturas', label: 'Facturas', icon: FileText },
  { to: '/pagos', label: 'Pagos', icon: Banknote },
  { to: '/usuarios', label: 'Usuarios', icon: Settings },
  { to: '/plantilla-clausulas', label: 'Plantilla de contrato', icon: ScrollText },
]

const NAV_EMPLEADO = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, fin: true },
  { to: '/contratos', label: 'Mis contratos', icon: FileSignature },
  { to: '/turnos', label: 'Mis turnos', icon: CalendarClock },
  { to: '/solicitudes', label: 'Mis solicitudes', icon: ClipboardList },
]

export default function Layout() {
  const { usuario, logout } = useAuth()
  const nav = usuario?.rol === 'admin' ? NAV_ADMIN : NAV_EMPLEADO

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="flex w-60 shrink-0 flex-col bg-slate-900 text-slate-100">
        <div className="px-5 py-5 text-lg font-semibold">Gestión de Servicios</div>
        <nav className="flex-1 space-y-0.5 px-2">
          {nav.map(({ to, label, icon: Icon, fin }) => (
            <NavLink
              key={to}
              to={to}
              end={fin}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded px-3 py-2 text-sm transition-colors ${
                  isActive ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 p-3">
          <NavLink to="/perfil" className="flex items-center gap-2.5 rounded px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white">
            <UserCircle size={17} />
            {usuario?.first_name || usuario?.username}
          </NavLink>
          <button
            onClick={logout}
            className="mt-1 flex w-full items-center gap-2.5 rounded px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <LogOut size={17} />
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-x-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
