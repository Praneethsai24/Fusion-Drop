import { useQuery } from '@tanstack/react-query'
import { ClipboardList } from 'lucide-react'
import { Link } from 'react-router-dom'
import { orderAPI } from '../services/api'
import OrderCard from '../components/order/OrderCard'
import Spinner from '../components/common/Spinner'
import styles from './OrdersPage.module.css'

export default function OrdersPage() {
  const { data: orders = [], isLoading } = useQuery({
    queryKey: ['my-orders'],
    queryFn: () => orderAPI.myOrders().then(r => r.data),
    refetchInterval: 30_000,
  })

  return (
    <div className="container" style={{ paddingBlock: 'var(--s10)' }}>
      <h1 className={styles.title}>My Orders</h1>
      {isLoading ? (
        <div style={{display:'flex',justifyContent:'center',padding:'var(--s16)'}}>
          <Spinner size={40} />
        </div>
      ) : orders.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><ClipboardList size={48}/></div>
          <h3>No orders yet</h3>
          <p>Place your first order to see it here.</p>
          <Link to="/restaurants" className="btn btn-primary">Browse Restaurants</Link>
        </div>
      ) : (
        <div className={styles.list}>
          {orders.map(o => <OrderCard key={o.id} order={o} />)}
        </div>
      )}
    </div>
  )
}