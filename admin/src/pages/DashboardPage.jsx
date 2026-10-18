import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorBanner, formatDate, Spinner } from '../components/ui'

export default function DashboardPage() {
  const { admin } = useAuth()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setStats(await api.overview())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">Dashboard</h1>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      <p className="muted">
        Welcome back, <strong>{admin?.username}</strong>. Live numbers, as of{' '}
        {stats ? formatDate(stats.generated_at) : '…'}.
      </p>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      {loading && !stats ? (
        <Spinner />
      ) : stats ? (
        <>
          <StatSection title="Players">
            <StatTile label="Total accounts" value={stats.users_total} />
            <StatTile label="Active" value={stats.users_active} />
            <StatTile label="Via Telegram" value={stats.users_via_telegram} />
            <StatTile label="New, last 24h" value={stats.users_new_24h} accent="ok" />
          </StatSection>

          <StatSection title="Gender (self-reported)">
            <StatTile label="Male" value={stats.demographics.gender.male} />
            <StatTile label="Female" value={stats.demographics.gender.female} />
            <StatTile label="Prefer not to say" value={stats.demographics.gender.undisclosed} />
            <StatTile label="Unknown" value={stats.demographics.gender.unknown} accent="warn" />
          </StatSection>

          <StatSection title="Age (self-reported)">
            <StatTile label="Under 18" value={stats.demographics.age_groups.under_18} />
            <StatTile label="18–24" value={stats.demographics.age_groups['18_24']} />
            <StatTile label="25–34" value={stats.demographics.age_groups['25_34']} />
            <StatTile label="35–44" value={stats.demographics.age_groups['35_44']} />
            <StatTile label="45+" value={stats.demographics.age_groups['45_plus']} />
            <StatTile label="Unknown" value={stats.demographics.age_groups.unknown} accent="warn" />
            <StatTile
              label="Average age"
              value={stats.demographics.average_age ?? '—'}
            />
            <StatTile
              label="Filled in the form"
              value={`${stats.demographics.answered} of ${stats.users_total}`}
              accent="ok"
            />
          </StatSection>

          <StatSection title="Coins">
            <StatTile label="In circulation" value={stats.coins_in_circulation} />
            <StatTile label="Issued (lifetime)" value={stats.coins_issued_total} accent="ok" />
            <StatTile label="Spent (lifetime)" value={stats.coins_spent_total} />
          </StatSection>

          <StatSection title="Bottle caps">
            <StatTile label="Active" value={stats.qr_codes_active} />
            <StatTile label="Redeemed" value={stats.qr_codes_redeemed} accent="ok" />
            <StatTile label="Expired" value={stats.qr_codes_expired} accent="warn" />
          </StatSection>

          <StatSection title="Catalog & battles">
            <StatTile label="Clothing items" value={stats.catalog_items_total} />
            <StatTile label="Available to buy" value={stats.catalog_items_available} accent="ok" />
            <StatTile label="Battles live now" value={stats.competitions_active} accent="ok" />
            <StatTile label="Battles finished" value={stats.competitions_completed} />
            <StatTile label="Votes cast" value={stats.votes_cast_total} />
            <StatTile
              label="Notifications pending"
              value={stats.notifications_pending}
              accent={stats.notifications_pending > 0 ? 'warn' : undefined}
            />
          </StatSection>
        </>
      ) : null}

      <h2 className="section-title">Manage</h2>
      <div className="card-grid">
        <Link className="card card-link" to="/competitions">
          <div className="card-title">Battles</div>
          <div className="card-desc">Watch every outfit battle live, not just your own.</div>
        </Link>
        <Link className="card card-link" to="/qr-codes">
          <div className="card-title">QR Codes</div>
          <div className="card-desc">Generate, inspect and manage redemption codes.</div>
        </Link>
        <Link className="card card-link" to="/users">
          <div className="card-title">Users</div>
          <div className="card-desc">Search accounts and manage activation status.</div>
        </Link>
        <Link className="card card-link" to="/clothing">
          <div className="card-title">Clothing</div>
          <div className="card-desc">Manage the clothing catalog users browse and buy.</div>
        </Link>
        <Link className="card card-link" to="/products">
          <div className="card-title">Products</div>
          <div className="card-desc">Manage products — QR codes link to these.</div>
        </Link>
      </div>
    </div>
  )
}

function StatSection({ title, children }) {
  return (
    <section className="stat-section">
      <h2 className="section-title">{title}</h2>
      <div className="stat-grid">{children}</div>
    </section>
  )
}

function StatTile({ label, value, accent }) {
  return (
    <div className={`stat-tile${accent ? ` stat-tile-${accent}` : ''}`}>
      <div className="stat-value">{Number(value).toLocaleString()}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
