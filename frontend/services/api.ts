import axios, { AxiosInstance, AxiosError } from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

// ── Request interceptor: inject access token ──────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor: auto refresh token on 401 ──────────────────────
let isRefreshing = false
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    error ? prom.reject(error) : prom.resolve(token!)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers!['Authorization'] = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        isRefreshing = false
        localStorage.clear()
        window.location.href = '/auth'
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        processQueue(null, data.access_token)
        originalRequest.headers!['Authorization'] = `Bearer ${data.access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        localStorage.clear()
        window.location.href = '/auth'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export default api