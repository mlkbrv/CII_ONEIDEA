import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { ErrorBanner, formatDate, Spinner } from '../components/ui'

const PAGE_SIZE = 20

export default function CompetitionsPage() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const searchTimer = useRef(null)

  useEffect(() => {
    clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => {
      setDebouncedQuery(query)
      setOffset(0)
    }, 300)
    return () => clearTimeout(searchTimer.current)
  }, [query])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { limit: PAGE_SIZE, offset }
      if (debouncedQuery) params.q = debouncedQuery
      if (status) params.status = status
      const data = await api.listCompetitions(params)
      setItems(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [offset, debouncedQuery, status])

  useEffect(() => {
    load()
  }, [load])

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const page = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">Battles</h1>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      <p className="muted">
        Every outfit battle, not just the ones you'd see as a participant — this is
        the one place to watch all of them at once.
      </p>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="toolbar">
        <label className="field field-inline search-field">
          <span>Search</span>
          <input
            type="search"
            placeholder="Either username…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <label className="field field-inline">
          <span>Status</span>
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value)
              setOffset(0)
            }}
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        <span className="muted toolbar-total">{total} battle(s)</span>
      </div>

      {loading ? (
        <Spinner />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Battle</th>
                <th>Status</th>
                <th>Score</th>
                <th>Prize pool</th>
                <th>Ends</th>
                <th>Started</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan="7" className="table-empty">
                    No battles found
                  </td>
                </tr>
              )}
              {items.map((row) => (
                <tr key={row.competition_id}>
                  <td>
                    <div className="battle-row">
                      <span>{row.challenger.username}</span>
                      <span className="battle-vs">vs</span>
                      <span>{row.opponent.username}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`pill ${row.status === 'active' ? 'pill-active' : 'pill-redeemed'}`}>
                      {row.status}
                    </span>
                  </td>
                  <td className="battle-score">
                    {row.challenger.votes} : {row.opponent.votes}
                  </td>
                  <td>{row.prize_pool} 🪙</td>
                  <td>{formatDate(row.end_time)}</td>
                  <td>{formatDate(row.start_time)}</td>
                  <td className="table-actions">
                    <Link className="btn btn-ghost btn-small" to={`/competitions/${row.competition_id}`}>
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pageCount > 1 && (
        <div className="pagination">
          <button
            className="btn btn-ghost btn-small"
            disabled={page <= 1}
            onClick={() => setOffset(offset - PAGE_SIZE)}
          >
            ← Prev
          </button>
          <span>
            Page {page} of {pageCount}
          </span>
          <button
            className="btn btn-ghost btn-small"
            disabled={page >= pageCount}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
