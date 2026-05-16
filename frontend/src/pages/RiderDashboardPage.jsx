import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bike, ToggleLeft, ToggleRight, MapPin } from 'lucide-react'
import toast from 'react-hot-toast'
import { riderAPI, orderAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import StatusBadge from '../components/common/StatusBadge'
import Spinner from '../components/common/Spinner'
import { fmt } from '../utils/helpers'
import styles from './RiderDashboardPage.module.css'

const NEXT = {
  order_received: 'rider_assigned',
  rider_assigned: 'picked_from_restaurant',
  picked_from_restaurant: 'all_items_picked',
  all_items_picked: 'out_for_delivery',
  out_for_delivery: 'delivered',
}

export default function RiderDashboardPage() {
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [available, setAvailable] = useState(user?.is_available ?? true)

  const { data: riders = [] } = useQuery({
    queryKey: ['riders'],
    queryFn: () => riderAPI.list().then(r => r.data),
    refetchInterval: 20_000,
  })

  const toggleMut = useMutation({
    mutationFn: (v) => riderAPI.updateAvailability(v),
    onSuccess: (_, v) => {
      setAvailable(v)
      toast.success(v ? 'You are now On Duty 🟢' : 'You are now Off Duty 🔴')
    },
  })

  // In a real app this would be filtered server-side to the rider's assigned orders.
  // For the demo we show all orders (limited to 10).
  const { data: recentOrders = [], isLoading } = useQuery({
    queryKey: ['rider-orders'],
    queryFn: () => orderAPI.myOrders({ limit: 10 }).then(r => r.data).catch(() => []),
    refetchInterval: 15_000,
  })

  const statusMut = useMutation({
    mutationFn: ({ id, status }) => orderAPI.updateStatus(id, { status }),
    onSuccess: () => { toast.success('Status updated'); qc.invalidateQueries(['rider-orders']) },
    onError: (e) => toast.error(e?.response?.data?.detail || 'Update failed'),
  })

  const myInfo = riders.find(r => r.id === user?.id)

  return (
    <div className="container" style={{ paddingBlock: 'var(--s10)' }}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.greeting}>
          <div className={styles.avatar}><Bike size={24} /></div>
          <div>
            <h1 className={styles.name}>Hey, {user?.name?.split(' ')[0]}!</h1>
            <p className={styles.sub}>{available ? '🟢 On duty — looking for orders' : '🔴 Off duty'}</p>
          </div>
        </div>
        <button
          className={`btn ${available ? 'btn-secondary' : 'btn-primary'}`}
          onClick={() => toggleMut.mutate(!available)}
          disabled={toggleMut.isPending}>
          {available ? <ToggleRight size={20}/> : <ToggleLeft size={20}/>}
          {available ? 'Go Off Duty' : 'Go On Duty'}
        </button>
      </div>

      {/* Stats */}
      <div className={styles.statsGrid}>
        {[
          { label: 'Status', value: available ? 'Available' : 'Unavailable', accent: available },
          { label: 'Vehicle', value: myInfo?.vehicle_type || user?.vehicle_type || '—' },
          { label: 'Location', value: myInfo?.current_lat ? `${Number(myInfo.current_lat).toFixed(4)}, ${Number(myInfo.current_lng).toFixed(4)}` : 'Unknown' },
          { label: 'Recent Deliveries', value: recentOrders.filter(o => o.status === 'delivered').length },
        ].map(s => (
          <div key={s.label} className={`card ${styles.statCard}`}>
            <div className={styles.statLabel}>{s.label}</div>
            <div className={`${styles.statValue} ${s.accent ? styles.accentValue : ''}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Active Orders */}
      <h2 className={styles.sectionTitle}>Active Orders</h2>
      {isLoading ? <Spinner size={32} /> : recentOrders.length === 0 ? (
        <div className="empty-state" style={{minHeight:'200px'}}>
          <p>No active orders assigned yet.</p>
        </div>
      ) : (
        <div className={styles.orderList}>
          {recentOrders.map(order => {
            const next = NEXT[order.status]
            return (
              <div key={order.id} className={`card ${styles.orderRow}`}>
                <div className={styles.orderLeft}>
                  <span className={styles.orderId}>Order #{order.id}</span>
                  <StatusBadge status={order.status} />
                </div>
                <div className={styles.orderMid}>
                  <MapPin size={14} />
                  <span>{order.delivery_address}</span>
                </div>
                <div className={styles.orderRight}>
                  <span className={styles.amount}>{fmt.currency(order.total_amount)}</span>
                  {next && (
                    <button className="btn btn-primary btn-sm"
                      disabled={statusMut.isPending}
                      onClick={() => statusMut.mutate({ id: order.id, status: next })}>
                      Mark: {next.replace(/_/g,' ')}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}