import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ArrowLeft, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { orderAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import OrderTracker from '../components/order/OrderTracker'
import StatusBadge from '../components/common/StatusBadge'
import Spinner from '../components/common/Spinner'
import { fmt } from '../utils/helpers'
import styles from './OrderDetailPage.module.css'

export default function OrderDetailPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const { isRider } = useAuthStore()

  const { data: order, isLoading } = useQuery({
    queryKey: ['order', id],
    queryFn: () => orderAPI.get(id).then(r => r.data),
  })

  const cancel = useMutation({
    mutationFn: () => orderAPI.cancel(id),
    onSuccess: () => { toast.success('Order cancelled'); qc.invalidateQueries(['order', id]) },
    onError: (e) => toast.error(e?.response?.data?.detail || 'Cannot cancel this order'),
  })

  if (isLoading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--s20)' }}>
      <Spinner size={48} />
    </div>
  )
  if (!order) return <div className="empty-state"><h3>Order not found</h3></div>

  const canCancel = !['picked_from_restaurant','all_items_picked','out_for_delivery','delivered','cancelled']
    .includes(order.status)

  return (
    <div className="container" style={{ paddingBlock: 'var(--s10)' }}>
      <Link to="/orders" className={`btn btn-ghost btn-sm ${styles.back}`}>
        <ArrowLeft size={16} /> Back to Orders
      </Link>

      <div className={styles.layout}>
        {/* Left — tracker + items */}
        <div className={styles.left}>
          <div className={`card ${styles.trackerCard}`}>
            <OrderTracker order={order} />
          </div>

          {/* Items breakdown */}
          <div className={`card ${styles.itemsCard}`}>
            <h2 className={styles.sectionTitle}>Items Ordered</h2>
            <ul className={styles.itemList}>
              {order.items?.map(item => (
                <li key={item.id} className={styles.itemRow}>
                  <span className={styles.itemName}>{item.menu_item_name || `Item #${item.menu_item_id}`}</span>
                  <span className={styles.itemQty}>×{item.quantity}</span>
                  <span className={styles.itemPrice}>{fmt.currency(item.unit_price * item.quantity)}</span>
                </li>
              ))}
            </ul>
            <hr className="divider" />
            <div className={styles.totals}>
              <div className={styles.totalRow}><span>Delivery Fee</span><span>{fmt.currency(order.delivery_fee)}</span></div>
              <div className={`${styles.totalRow} ${styles.grandTotal}`}>
                <span>Total</span><span>{fmt.currency(order.total_amount)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right — meta */}
        <div className={styles.right}>
          <div className={`card ${styles.metaCard}`}>
            <h2 className={styles.sectionTitle}>Order Details</h2>
            <dl className={styles.metaList}>
              <dt>Order ID</dt>    <dd>#{order.id}</dd>
              <dt>Status</dt>      <dd><StatusBadge status={order.status} /></dd>
              <dt>Placed</dt>      <dd>{fmt.date(order.created_at)}</dd>
              <dt>Address</dt>     <dd>{order.delivery_address}</dd>
              {order.is_batched && <><dt>Batched</dt><dd><span className="badge badge-info">Yes — shared delivery</span></dd></>}
              {order.estimated_eta_minutes && <><dt>ETA</dt><dd>{order.estimated_eta_minutes} minutes</dd></>}
            </dl>

            {canCancel && !isRider() && (
              <button
                className="btn btn-outline"
                style={{ width: '100%', justifyContent: 'center', marginTop: 'var(--s4)', borderColor: 'var(--error)', color: 'var(--error)' }}
                disabled={cancel.isPending}
                onClick={() => cancel.mutate()}>
                {cancel.isPending ? <Spinner size={16} color="var(--error)" /> : <XCircle size={16} />}
                Cancel Order
              </button>
            )}
          </div>

          {/* Rider status update (riders only) */}
          {isRider() && <RiderControls orderId={order.id} currentStatus={order.status} />}
        </div>
      </div>
    </div>
  )
}

const NEXT_STATUS = {
  order_received:   'rider_assigned',
  rider_assigned:   'picked_from_restaurant',
  picked_from_restaurant: 'all_items_picked',
  all_items_picked: 'out_for_delivery',
  out_for_delivery: 'delivered',
}

function RiderControls({ orderId, currentStatus }) {
  const qc = useQueryClient()
  const next = NEXT_STATUS[currentStatus]

  const update = useMutation({
    mutationFn: (status) => orderAPI.updateStatus(orderId, { status }),
    onSuccess: () => { toast.success('Status updated'); qc.invalidateQueries(['order', orderId]) },
    onError:   (e) => toast.error(e?.response?.data?.detail || 'Update failed'),
  })

  if (!next) return null
  return (
    <div className={`card ${styles.metaCard}`}>
      <h2 className={styles.sectionTitle}>Rider Controls</h2>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginBottom: 'var(--s4)' }}>
        Current status: <StatusBadge status={currentStatus} />
      </p>
      <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}
        disabled={update.isPending} onClick={() => update.mutate(next)}>
        {update.isPending ? <Spinner size={16} color="#fff" /> : 'Mark: ' + next.replace(/_/g, ' ')}
      </button>
    </div>
  )
}