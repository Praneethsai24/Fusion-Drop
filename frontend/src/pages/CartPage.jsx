import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { ShoppingBag, MapPin, ArrowRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { orderAPI } from '../services/api'
import { useCartStore } from '../store/cartStore'
import { useAuthStore } from '../store/authStore'
import CartItem from '../components/order/CartItem'
import Spinner from '../components/common/Spinner'
import { fmt } from '../utils/helpers'
import styles from './CartPage.module.css'

const DELIVERY_FEE = 30

export default function CartPage() {
  const navigate = useNavigate()
  const { items, subtotal, clearCart, deliveryAddress, setDeliveryInfo } = useCartStore()
  const { isAuthenticated } = useAuthStore()
  const [address, setAddress] = useState(deliveryAddress || '')
  const [lat, setLat] = useState('12.9716')
  const [lng, setLng]  = useState('77.5946')

  const checkout = useMutation({
    mutationFn: () => orderAPI.checkout({
      items: items.map(i => ({ menu_item_id: i.menuItem.id, quantity: i.quantity })),
      delivery_address: address,
      delivery_lat: parseFloat(lat),
      delivery_lng: parseFloat(lng),
    }),
    onSuccess: (res) => {
      clearCart()
      toast.success('Order placed! Track it live.')
      navigate(`/orders/${res.data.id}`)
    },
    onError: (e) => toast.error(e?.response?.data?.detail || 'Checkout failed'),
  })

  const total = subtotal() + DELIVERY_FEE

  if (items.length === 0) return (
    <div className="container" style={{ paddingBlock: 'var(--s20)' }}>
      <div className="empty-state">
        <div className="empty-state-icon"><ShoppingBag size={48} /></div>
        <h3>Your cart is empty</h3>
        <p>Add items from a restaurant to get started.</p>
        <Link to="/restaurants" className="btn btn-primary">Browse Restaurants</Link>
      </div>
    </div>
  )

  return (
    <div className="container" style={{ paddingBlock: 'var(--s10)' }}>
      <h1 className={styles.title}>Your Cart</h1>
      <div className={styles.layout}>

        {/* Items */}
        <div className={styles.items}>
          <div className={`card ${styles.itemsCard}`}>
            <h2 className={styles.sectionTitle}>
              <ShoppingBag size={18} /> Items ({items.length})
            </h2>
            {items.map(item => <CartItem key={item.menuItem.id} item={item} />)}
          </div>

          {/* Delivery address */}
          <div className={`card ${styles.addressCard}`}>
            <h2 className={styles.sectionTitle}><MapPin size={18} /> Delivery Address</h2>
            <div className="input-group">
              <label className="input-label">Full Address</label>
              <input className="input" value={address}
                onChange={e => setAddress(e.target.value)}
                placeholder="e.g. 42 Indiranagar 12th Main, Bengaluru" />
            </div>
            <div className={styles.coordRow}>
              <div className="input-group" style={{ flex: 1 }}>
                <label className="input-label">Latitude</label>
                <input className="input" type="number" value={lat}
                  onChange={e => setLat(e.target.value)} step="0.0001" />
              </div>
              <div className="input-group" style={{ flex: 1 }}>
                <label className="input-label">Longitude</label>
                <input className="input" type="number" value={lng}
                  onChange={e => setLng(e.target.value)} step="0.0001" />
              </div>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className={styles.summary}>
          <div className={`card ${styles.summaryCard}`}>
            <h2 className={styles.sectionTitle}>Order Summary</h2>
            <div className={styles.summaryLine}>
              <span>Subtotal</span><span>{fmt.currency(subtotal())}</span>
            </div>
            <div className={styles.summaryLine}>
              <span>Delivery Fee</span><span>{fmt.currency(DELIVERY_FEE)}</span>
            </div>
            {items.length > 1 && (
              <div className={styles.summaryLine} style={{ color: 'var(--success)' }}>
                <span>🎉 Multi-restaurant discount</span><span>−₹7.50</span>
              </div>
            )}
            <hr className="divider" />
            <div className={`${styles.summaryLine} ${styles.totalLine}`}>
              <span>Total</span><span>{fmt.currency(total)}</span>
            </div>

            {!isAuthenticated() ? (
              <div>
                <p className={styles.loginNote}>You need to sign in to place an order.</p>
                <Link to="/login" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                  Sign In to Continue
                </Link>
              </div>
            ) : (
              <button
                className="btn btn-primary btn-lg"
                style={{ width: '100%', justifyContent: 'center' }}
                disabled={checkout.isPending || !address.trim()}
                onClick={() => { setDeliveryInfo(address, lat, lng); checkout.mutate() }}>
                {checkout.isPending ? <><Spinner size={18} color="#fff" /> Placing Order…</> : <>Place Order <ArrowRight size={18} /></>}
              </button>
            )}
            <p className={styles.notice}>
              🚴 Smart batching may group your order with nearby deliveries to save time and cost.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}