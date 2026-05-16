import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ShoppingBag, Plus, Check, Clock, MapPin } from 'lucide-react'
import toast from 'react-hot-toast'
import { restaurantAPI } from '../services/api'
import { useCartStore } from '../store/cartStore'
import { fmt } from '../utils/helpers'
import Spinner from '../components/common/Spinner'
import StarRating from '../components/common/StarRating'
import styles from './RestaurantDetailPage.module.css'

export default function RestaurantDetailPage() {
  const { id } = useParams()
  const [added, setAdded] = useState({})
  const { addItem, items } = useCartStore()

  const { data: restaurant, isLoading } = useQuery({
    queryKey: ['restaurant', id],
    queryFn: () => restaurantAPI.get(id).then(r => r.data),
  })

  if (isLoading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--s20)' }}>
      <Spinner size={48} />
    </div>
  )
  if (!restaurant) return <div className="empty-state"><h3>Restaurant not found</h3></div>

  const handleAdd = (item) => {
    addItem(item, restaurant.id, restaurant.name)
    setAdded(prev => ({ ...prev, [item.id]: true }))
    setTimeout(() => setAdded(prev => ({ ...prev, [item.id]: false })), 1200)
    toast.success(`${item.name} added to cart`)
  }

  // Group menu by category
  const byCategory = (restaurant.menu_items || []).reduce((acc, item) => {
    const cat = item.category || 'Menu'
    acc[cat] = acc[cat] ? [...acc[cat], item] : [item]
    return acc
  }, {})

  return (
    <div>
      {/* Hero banner */}
      <div className={styles.hero}>
        <div className={`${styles.heroInner} container`}>
          <div className={styles.heroEmoji}>
            {restaurant.cuisine_type === 'Indian' ? '🍛' :
             restaurant.cuisine_type === 'American' ? '🍔' :
             restaurant.cuisine_type === 'Japanese' ? '🍱' :
             restaurant.cuisine_type === 'Italian' ? '🍝' : '🍽️'}
          </div>
          <div className={styles.heroInfo}>
            <h1 className={styles.name}>{restaurant.name}</h1>
            <p className={styles.desc}>{restaurant.description}</p>
            <div className={styles.meta}>
              <StarRating value={restaurant.rating || 0} />
              <span className={styles.sep}>·</span>
              <span><Clock size={14} /> {restaurant.avg_prep_time_minutes} min prep</span>
              <span className={styles.sep}>·</span>
              <span><MapPin size={14} /> {restaurant.address}</span>
            </div>
          </div>
        </div>
      </div>

      <div className={`${styles.layout} container`}>
        {/* Menu */}
        <div className={styles.menu}>
          {Object.entries(byCategory).map(([cat, items]) => (
            <div key={cat} className={styles.category}>
              <h2 className={styles.catTitle}>{cat}</h2>
              <div className={styles.itemGrid}>
                {items.map(item => {
                  const inCart = useCartStore.getState().items.find(i => i.menuItem.id === item.id)
                  return (
                    <div key={item.id} className={`card ${styles.menuItem}`}>
                      <div className={styles.itemInfo}>
                        <h3 className={styles.itemName}>{item.name}</h3>
                        <p className={styles.itemDesc}>{item.description}</p>
                        <div className={styles.itemFooter}>
                          <span className={styles.itemPrice}>{fmt.currency(item.price)}</span>
                          {inCart && (
                            <span className={styles.inCartLabel}>×{inCart.quantity} in cart</span>
                          )}
                        </div>
                      </div>
                      <button
                        className={`btn ${added[item.id] ? 'btn-secondary' : 'btn-primary'} btn-sm ${styles.addBtn}`}
                        onClick={() => handleAdd(item)}
                        disabled={item.is_available === false}>
                        {item.is_available === false ? 'Sold Out' :
                         added[item.id] ? <><Check size={14}/> Added</> :
                         <><Plus size={14}/> Add</>}
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Sticky cart preview */}
        <div className={styles.cartPreview}>
          <CartPreview restaurantId={restaurant.id} />
        </div>
      </div>
    </div>
  )
}

function CartPreview({ restaurantId }) {
  const { items, subtotal, totalItems } = useCartStore()
  const forThisRestaurant = items.filter(i => i.restaurantId === restaurantId)
  if (forThisRestaurant.length === 0) return (
    <div className={`card ${styles.emptyCart}`}>
      <ShoppingBag size={32} style={{ color: 'var(--text-faint)', margin: '0 auto var(--s3)' }} />
      <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
        Add items to get started
      </p>
    </div>
  )
  return (
    <div className={`card ${styles.cartCard}`}>
      <div className={styles.cartHeader}>
        <ShoppingBag size={18} />
        <span>{totalItems()} item{totalItems() !== 1 ? 's' : ''}</span>
      </div>
      <ul className={styles.cartList}>
        {forThisRestaurant.map(i => (
          <li key={i.menuItem.id} className={styles.cartLine}>
            <span>{i.menuItem.name} ×{i.quantity}</span>
            <span>{fmt.currency(i.menuItem.price * i.quantity)}</span>
          </li>
        ))}
      </ul>
      <div className={styles.cartTotal}>
        <span>Subtotal</span><span>{fmt.currency(subtotal())}</span>
      </div>
      <a href="/cart" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
        View Cart
      </a>
    </div>
  )
}