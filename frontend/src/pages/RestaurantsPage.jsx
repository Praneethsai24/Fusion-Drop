import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { restaurantAPI } from '../services/api'
import RestaurantCard from '../components/restaurant/RestaurantCard'
import Spinner from '../components/common/Spinner'
import styles from './RestaurantsPage.module.css'

const CUISINES = ['All', 'Indian', 'American', 'Japanese', 'Italian', 'Chinese', 'Mexican']

export default function RestaurantsPage() {
  const [search, setSearch]   = useState('')
  const [cuisine, setCuisine] = useState('All')

  const { data: restaurants = [], isLoading } = useQuery({
    queryKey: ['restaurants', cuisine],
    queryFn: () => restaurantAPI.list(cuisine !== 'All' ? { cuisine } : {}).then(r => r.data),
  })

  const filtered = restaurants.filter(r =>
    r.name.toLowerCase().includes(search.toLowerCase()) ||
    r.description?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="container" style={{ paddingBlock: 'var(--s10)' }}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Restaurants</h1>
          <p className={styles.sub}>{restaurants.length} restaurants open near you</p>
        </div>
        <div className="input-icon-wrap" style={{ width: '280px' }}>
          <Search size={16} className="icon-left" />
          <input className="input" placeholder="Search restaurants…"
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      {/* Cuisine filter */}
      <div className={styles.filters}>
        {CUISINES.map(c => (
          <button key={c}
            className={`btn btn-sm ${cuisine === c ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setCuisine(c)}>
            {c}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--s16)' }}>
          <Spinner size={40} />
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon" style={{ fontSize: '3rem' }}>🍽️</div>
          <h3>No restaurants found</h3>
          <p>Try a different search term or cuisine filter.</p>
          <button className="btn btn-secondary" onClick={() => { setSearch(''); setCuisine('All') }}>
            Clear Filters
          </button>
        </div>
      ) : (
        <div className={styles.grid}>
          {filtered.map(r => <RestaurantCard key={r.id} restaurant={r} />)}
        </div>
      )}
    </div>
  )
}