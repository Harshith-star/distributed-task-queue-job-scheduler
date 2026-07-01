import axios from 'axios';
import toast from 'react-hot-toast';

const api = axios.create({ baseURL: '/api/v1', timeout: 30_000 });

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  r => r,
  async err => {
    const orig = err.config;
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh });
          localStorage.setItem('access_token',  data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          orig.headers.Authorization = `Bearer ${data.access_token}`;
          return api(orig);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      } else {
        localStorage.clear();
        window.location.href = '/login';
      }
    }
    const msg = err.response?.data?.detail || 'Something went wrong';
    if (err.response?.status !== 401) toast.error(msg);
    return Promise.reject(err);
  }
);

export default api;
