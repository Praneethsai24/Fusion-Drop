import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Eye, EyeOff, Mail, Lock, User, Phone, Bike } from 'lucide-react'
import toast from 'react-hot-toast'
import { authAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import Spinner from '../components/common/Spinner'
import styles from './AuthPages.module.css'

// ─── Login ─────────────────────────────────────────────────────────────────
export function LoginPage() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [show, setShow]  = useState(false)
  const { login } = useAuthStore()
  const navigate   = useNavigate()
  const location   = useLocation()
  const from = location.state?.from?.pathname || '/'

  const mut = useMutation({
    mutationFn: () => authAPI.login(form),
    onSuccess: (res) => {
      login(res.data)
      toast.success(`Welcome back, ${res.data.name?.split(' ')[0]}!`)
      navigate(from, { replace: true })
    },
    onError: (e) => toast.error(e?.response?.data?.detail || 'Login failed'),
  })

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logoWrap}>
          <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="16" fill="var(--brand)"/>
            <path d="M9 22 C9 14 16 8 16 8 C16 8 23 14 23 22 C23 26 16 28 16 28 C16 28 9 26 9 22Z"
                  fill="white" opacity="0.9"/>
            <circle cx="16" cy="20" r="3" fill="var(--brand)"/>
          </svg>
          <span className={styles.brandName}>FusionDrop</span>
        </div>
        <h1 className={styles.title}>Welcome back</h1>
        <p className={styles.sub}>Sign in to your account</p>

        <form className={styles.form} onSubmit={e => { e.preventDefault(); mut.mutate() }}>
          <div className="input-group">
            <label className="input-label">Email</label>
            <div className="input-icon-wrap">
              <Mail size={16} className="icon-left" />
              <input className="input" type="email" placeholder="you@example.com"
                value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} required />
            </div>
          </div>
          <div className="input-group">
            <label className="input-label">Password</label>
            <div className="input-icon-wrap" style={{ position: 'relative' }}>
              <Lock size={16} className="icon-left" />
              <input className="input" type={show ? 'text' : 'password'} placeholder="••••••••"
                value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                style={{ paddingRight: '2.75rem' }} required />
              <button type="button" onClick={() => setShow(s => !s)}
                style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)',
                         background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                {show ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          <button type="submit" className="btn btn-primary btn-lg"
            style={{ width: '100%', justifyContent: 'center' }} disabled={mut.isPending}>
            {mut.isPending ? <><Spinner size={18} color="#fff" /> Signing In…</> : 'Sign In'}
          </button>
        </form>

        <p className={styles.switch}>
          Don't have an account? <Link to="/signup" className={styles.link}>Sign up</Link>
        </p>

        <div className={styles.demoBox}>
          <p className={styles.demoTitle}>Demo credentials</p>
          <div className={styles.demoGrid}>
            <button className="btn btn-secondary btn-sm" onClick={() =>
              setForm({ email: 'demo@fusiondrop.in', password: 'demo1234' })}>
              👤 Customer
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() =>
              setForm({ email: 'arjun@fusiondrop.in', password: 'rider123' })}>
              🚴 Rider
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Signup ────────────────────────────────────────────────────────────────
export function SignupPage() {
  const [role, setRole]  = useState('customer')
  const [show, setShow]  = useState(false)
  const [form, setForm]  = useState({
    name: '', email: '', password: '', phone: '',
    vehicle_type: 'bike', current_lat: '12.9716', current_lng: '77.5946',
  })
  const { login } = useAuthStore()
  const navigate   = useNavigate()

  const upd = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const mut = useMutation({
    mutationFn: () => role === 'customer'
      ? authAPI.customerSignup({ name: form.name, email: form.email, password: form.password, phone: form.phone })
      : authAPI.riderSignup({
          name: form.name, email: form.email, password: form.password,
          vehicle_type: form.vehicle_type,
          current_lat: parseFloat(form.current_lat),
          current_lng: parseFloat(form.current_lng),
        }),
    onSuccess: (res) => {
      login(res.data)
      toast.success(`Welcome, ${res.data.name?.split(' ')[0]}! 🎉`)
      navigate(role === 'rider' ? '/rider/dashboard' : '/restaurants')
    },
    onError: (e) => toast.error(e?.response?.data?.detail || 'Signup failed'),
  })

  return (
    <div className={styles.page}>
      <div className={`${styles.card} ${styles.cardWide}`}>
        <div className={styles.logoWrap}>
          <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="16" fill="var(--brand)"/>
            <path d="M9 22 C9 14 16 8 16 8 C16 8 23 14 23 22 C23 26 16 28 16 28 C16 28 9 26 9 22Z" fill="white" opacity="0.9"/>
            <circle cx="16" cy="20" r="3" fill="var(--brand)"/>
          </svg>
          <span className={styles.brandName}>FusionDrop</span>
        </div>
        <h1 className={styles.title}>Create your account</h1>

        {/* Role toggle */}
        <div className={styles.roleToggle}>
          <button className={`btn ${role === 'customer' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setRole('customer')}><User size={16}/> Customer</button>
          <button className={`btn ${role === 'rider' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setRole('rider')}><Bike size={16}/> Rider</button>
        </div>

        <form className={styles.form} onSubmit={e => { e.preventDefault(); mut.mutate() }}>
          <div className={styles.formGrid}>
            <div className="input-group">
              <label className="input-label">Full Name</label>
              <div className="input-icon-wrap">
                <User size={16} className="icon-left" />
                <input className="input" placeholder="Praneeth Sai"
                  value={form.name} onChange={e => upd('name', e.target.value)} required />
              </div>
            </div>
            <div className="input-group">
              <label className="input-label">Email</label>
              <div className="input-icon-wrap">
                <Mail size={16} className="icon-left" />
                <input className="input" type="email" placeholder="you@example.com"
                  value={form.email} onChange={e => upd('email', e.target.value)} required />
              </div>
            </div>
            <div className="input-group">
              <label className="input-label">Password</label>
              <div className="input-icon-wrap" style={{ position: 'relative' }}>
                <Lock size={16} className="icon-left" />
                <input className="input" type={show ? 'text' : 'password'} placeholder="Min 8 characters"
                  value={form.password} onChange={e => upd('password', e.target.value)}
                  style={{ paddingRight: '2.75rem' }} required minLength={8} />
                <button type="button" onClick={() => setShow(s=>!s)}
                  style={{ position:'absolute',right:'0.75rem',top:'50%',transform:'translateY(-50%)',background:'none',border:'none',cursor:'pointer',color:'var(--text-muted)' }}>
                  {show ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
            </div>
            {role === 'customer' && (
              <div className="input-group">
                <label className="input-label">Phone (optional)</label>
                <div className="input-icon-wrap">
                  <Phone size={16} className="icon-left" />
                  <input className="input" type="tel" placeholder="9876543210"
                    value={form.phone} onChange={e => upd('phone', e.target.value)} />
                </div>
              </div>
            )}
            {role === 'rider' && <>
              <div className="input-group">
                <label className="input-label">Vehicle Type</label>
                <select className="input select" value={form.vehicle_type}
                  onChange={e => upd('vehicle_type', e.target.value)}>
                  <option value="bike">Bike</option>
                  <option value="scooter">Scooter</option>
                  <option value="cycle">Cycle</option>
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Starting Latitude</label>
                <input className="input" type="number" step="0.0001"
                  value={form.current_lat} onChange={e => upd('current_lat', e.target.value)} />
              </div>
            </>}
          </div>

          <button type="submit" className="btn btn-primary btn-lg"
            style={{ width: '100%', justifyContent: 'center' }} disabled={mut.isPending}>
            {mut.isPending ? <><Spinner size={18} color="#fff" /> Creating Account…</> : 'Create Account'}
          </button>
        </form>

        <p className={styles.switch}>
          Already have an account? <Link to="/login" className={styles.link}>Sign in</Link>
        </p>
      </div>
    </div>
  )
}