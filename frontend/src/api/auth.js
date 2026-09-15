import client from './client'

export const authApi = {
  login: (email, password, codigo_2fa) =>
    client.post('/auth/login/', { email, password, ...(codigo_2fa ? { codigo_2fa } : {}) }).then((r) => r.data),
  logout: (refresh) => client.post('/auth/logout/', { refresh }).then((r) => r.data),
  perfil: () => client.get('/auth/perfil/').then((r) => r.data),
  actualizarPerfil: (data) => client.patch('/auth/perfil/', data).then((r) => r.data),
  cambiarPassword: (password_actual, password_nueva) =>
    client.post('/auth/cambiar-password/', { password_actual, password_nueva }).then((r) => r.data),
  solicitarRecuperacion: (email) => client.post('/auth/solicitar-recuperacion/', { email }).then((r) => r.data),
  restablecerPassword: (uid, token, password_nueva) =>
    client.post('/auth/restablecer-password/', { uid, token, password_nueva }).then((r) => r.data),
  estado2fa: () => client.get('/auth/2fa/estado/').then((r) => r.data),
  setup2fa: () => client.get('/auth/2fa/setup/').then((r) => r.data),
  verificar2fa: (codigo) => client.post('/auth/2fa/verificar/', { codigo }).then((r) => r.data),
  verificarPassword: (data) => client.post('/auth/verificar-password/', data).then((r) => r.data),
  verificarUsername: (username) =>
    client.get('/auth/verificar-username/', { params: { username } }).then((r) => r.data),
  listaUsuarios: () => client.get('/auth/usuarios/').then((r) => r.data),
  crearUsuario: (data) => client.post('/auth/crear-usuario/', data).then((r) => r.data),
  actualizarUsuario: (id, data) => client.patch(`/auth/usuarios/${id}/`, data).then((r) => r.data),
  eliminarUsuario: (id) => client.delete(`/auth/usuarios/${id}/`).then((r) => r.data),
  dashboardStats: () => client.get('/dashboard/stats/').then((r) => r.data),
  dashboardMensual: () => client.get('/dashboard/mensual/').then((r) => r.data),
}
