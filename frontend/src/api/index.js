import api from './client';

// ── Auth ──────────────────────────────────────────────────────────────────
export const authApi = {
  register:       (data)  => api.post('/auth/register', data),
  login:          (data)  => api.post('/auth/login', data),
  logout:         (tok)   => api.post('/auth/logout', { refresh_token: tok }),
  me:             ()      => api.get('/auth/me'),
  updateProfile:  (data)  => api.put('/auth/me', data),
  changePassword: (data)  => api.post('/auth/change-password', data),
};

// ── Tasks ─────────────────────────────────────────────────────────────────
export const tasksApi = {
  list:     (params) => api.get('/tasks', { params }),
  get:      (id)     => api.get(`/tasks/${id}`),
  create:   (data)   => api.post('/tasks', data),
  update:   (id, d)  => api.put(`/tasks/${id}`, d),
  delete:   (id)     => api.delete(`/tasks/${id}`),
  pause:    (id)     => api.post(`/tasks/${id}/pause`),
  resume:   (id)     => api.post(`/tasks/${id}/resume`),
  trigger:  (id)     => api.post(`/tasks/${id}/trigger`),
};

// ── Executions ────────────────────────────────────────────────────────────
export const executionsApi = {
  list:   (params) => api.get('/executions', { params }),
  get:    (id)     => api.get(`/executions/${id}`),
  retry:  (id)     => api.post(`/executions/${id}/retry`),
  cancel: (id)     => api.post(`/executions/${id}/cancel`),
};

// ── Dashboard / Analytics ─────────────────────────────────────────────────
export const dashboardApi = {
  stats:     ()        => api.get('/dashboard/stats'),
  analytics: (days=14) => api.get('/analytics', { params: { days } }),
};

// ── Notifications ─────────────────────────────────────────────────────────
export const notifApi = {
  list:     (params) => api.get('/audit/notifications', { params }),
  markRead: (ids)    => api.post('/audit/notifications/read', { notification_ids: ids }),
};

// ── Audit ─────────────────────────────────────────────────────────────────
export const auditApi = {
  logs: (params) => api.get('/audit/logs', { params }),
};

// ── Admin ─────────────────────────────────────────────────────────────────
export const adminApi = {
  users:         (params) => api.get('/admin/users', { params }),
  toggleUser:    (id, active) => api.patch(`/admin/users/${id}/activate`, null, { params: { active } }),
  workerStatus:  () => api.get('/admin/workers/status'),
};
