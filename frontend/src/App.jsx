import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Navbar from './components/layout/Navbar'
import HomePage            from './pages/HomePage'
import RestaurantsPage     from './pages/RestaurantsPage'
import RestaurantDetailPage from './pages/RestaurantDetailPage'
import CartPage            from './pages/CartPage'
import OrdersPage          from './pages/OrdersPage'
import OrderDetailPage     from './pages/OrderDetailPage'
import RiderDashboardPage  from './pages/RiderDashboardPage'
import { LoginPage, SignupPage } from './pages/AuthPages'
import styles from './App.module.css'

function ProtectedRoute({ children, requireRole }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated()) return <Navigate to="/login" replace />
  if (requireRole && user?.role !== requireRole) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <div className={styles.app}>
      <Navbar />
      <main className={styles.main}>
        <Routes>
          <Route path="/"                  element={<HomePage />} />
          <Route path="/restaurants"       element={<RestaurantsPage />} />
          <Route path="/restaurants/:id"   element={<RestaurantDetailPage />} />
          <Route path="/login"             element={<LoginPage />} />
          <Route path="/signup"            element={<SignupPage />} />
          <Route path="/cart"              element={<CartPage />} />
          <Route path="/orders"            element={
            <ProtectedRoute><OrdersPage /></ProtectedRoute>
          } />
          <Route path="/orders/:id"        element={
            <ProtectedRoute><OrderDetailPage /></ProtectedRoute>
          } />
          <Route path="/rider/dashboard"   element={
            <ProtectedRoute requireRole="rider"><RiderDashboardPage /></ProtectedRoute>
          } />
          <Route path="*" element={
            <div className="empty-state" style={{minHeight:'60vh'}}>
              <h3>404 — Page not found</h3>
              <p>The page you're looking for doesn't exist.</p>
              <a href="/" className="btn btn-primary">Go Home</a>
            </div>
          } />
        </Routes>
      </main>
      <footer className={styles.footer}>
        <div className="container" style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:'var(--s4)',flexWrap:'wrap'}}>
          <span>© 2025 FusionDrop</span>
          <span style={{color:'var(--text-muted)',fontSize:'var(--text-xs)'}}>Built with FastAPI + React</span>
        </div>
      </footer>
    </div>
  )
}