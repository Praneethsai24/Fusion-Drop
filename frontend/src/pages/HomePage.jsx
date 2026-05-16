import { Link } from 'react-router-dom'
import { Bike, Zap, ShieldCheck, ArrowRight, Star } from 'lucide-react'
import styles from './HomePage.module.css'

const FEATURES = [
  { icon: Zap,        title: 'Lightning Fast',    desc: 'Order from multiple restaurants in one checkout. Smart batching cuts your wait time.' },
  { icon: Bike,       title: 'Live Tracking',     desc: 'Watch your rider move in real-time via WebSocket. No more wondering where your food is.' },
  { icon: ShieldCheck,title: 'Secure & Reliable', desc: 'JWT-secured accounts, encrypted payments, and order history always at your fingertips.' },
]

const TESTIMONIALS = [
  { name: 'Rohan S.',  city: 'Bengaluru', text: 'Ordered sushi AND a burger in one go. Arrived together, hot. Magic.', rating: 5 },
  { name: 'Priya K.',  city: 'Hyderabad', text: 'The live tracker is genuinely addictive. I watch it the whole time.', rating: 5 },
  { name: 'Akash M.',  city: 'Bengaluru', text: 'Cheapest delivery fee I\'ve found. The batching discount is real.', rating: 4 },
]

export default function HomePage() {
  return (
    <div className={styles.page}>

      {/* ── Hero ── */}
      <section className={styles.hero}>
        <div className={`${styles.heroInner} container`}>
          <div className={styles.heroBadge}>
            <span className="badge badge-brand">🚀 Now live in Bengaluru</span>
          </div>
          <h1 className={styles.heroTitle}>
            Order from <em className={styles.accent}>anywhere</em>,<br />
            delivered together.
          </h1>
          <p className={styles.heroSub}>
            Mix dishes from multiple restaurants in a single order.
            Real-time tracking. Intelligent batching. No compromise.
          </p>
          <div className={styles.heroCtas}>
            <Link to="/restaurants" className="btn btn-primary btn-lg">
              Browse Restaurants <ArrowRight size={18} />
            </Link>
            <Link to="/signup" className="btn btn-secondary btn-lg">
              Create Account
            </Link>
          </div>
        </div>
        <div className={styles.heroVisual}>
          <div className={styles.heroCard}>
            <div className={styles.heroEmoji}>🍔</div>
            <div className={styles.heroLine}>
              <span>Burger Barn</span>
              <span className="badge badge-success">On the Way</span>
            </div>
          </div>
          <div className={`${styles.heroCard} ${styles.heroCardOffset}`}>
            <div className={styles.heroEmoji}>🍛</div>
            <div className={styles.heroLine}>
              <span>Spice Garden</span>
              <span className="badge badge-warning">Picked Up</span>
            </div>
          </div>
          <div className={styles.heroRider}>
            <Bike size={24} />
            <span>Arjun • 8 min away</span>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className={styles.features}>
        <div className="container">
          <h2 className={styles.sectionTitle}>Why FusionDrop?</h2>
          <div className={styles.featureGrid}>
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div key={title} className={`card ${styles.featureCard}`}>
                <div className={styles.featureIcon}><Icon size={22} /></div>
                <h3 className={styles.featureTitle}>{title}</h3>
                <p className={styles.featureDesc}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className={styles.howItWorks}>
        <div className="container">
          <h2 className={styles.sectionTitle}>How it works</h2>
          <div className={styles.steps}>
            {['Browse & add items from any restaurant',
              'One checkout — we batch nearby orders',
              'A single rider picks everything up',
              'Live track right to your door'].map((s, i) => (
              <div key={i} className={styles.step}>
                <div className={styles.stepNum}>{i + 1}</div>
                <p className={styles.stepText}>{s}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ── */}
      <section className={styles.testimonials}>
        <div className="container">
          <h2 className={styles.sectionTitle}>What our customers say</h2>
          <div className={styles.testimonialGrid}>
            {TESTIMONIALS.map((t) => (
              <div key={t.name} className={`card ${styles.testimonialCard}`}>
                <div className={styles.tStars}>
                  {Array.from({ length: t.rating }).map((_, i) => <Star key={i} size={14} fill="currentColor" />)}
                </div>
                <p className={styles.tText}>"{t.text}"</p>
                <div className={styles.tAuthor}>
                  <div className={styles.tAvatar}>{t.name[0]}</div>
                  <div>
                    <div className={styles.tName}>{t.name}</div>
                    <div className={styles.tCity}>{t.city}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className={styles.cta}>
        <div className="container">
          <div className={styles.ctaBox}>
            <h2>Ready to fuse your order?</h2>
            <p>Join thousands of happy customers across Bengaluru.</p>
            <Link to="/signup" className="btn btn-primary btn-lg">
              Get Started — It's Free <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>

    </div>
  )
}