import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { ErrorBanner, formatDate, Spinner, StatusPill } from '../components/ui'

// Same order the Mini App paints in (miniapp/src/components/AvatarView.jsx) —
// listing slots any other order would make an outfit read differently here
// than it looks in the app, which is exactly the kind of mismatch an
// operator checking a dispute needs this page to NOT have.
const SLOT_ORDER = ['hair', 'hat', 'top', 'bottom', 'shoes', 'accessory']

export default function CompetitionDetailPage() {
  const { competitionId } = useParams()
  const [battle, setBattle] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .getCompetition(competitionId)
      .then((data) => {
        if (!cancelled) setBattle(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [competitionId])

  if (loading) return <Spinner />
  if (error && !battle) {
    return (
      <div>
        <Link className="btn btn-ghost btn-small" to="/competitions">← Back</Link>
        <ErrorBanner message={error} />
      </div>
    )
  }
  if (!battle) return null

  const rows = [
    ['Status', <StatusPill status={battle.status} />],
    ['Score', `${battle.challenger.votes} : ${battle.opponent.votes}`],
    ['Total votes', String(battle.total_votes)],
    ['Prize pool', `${battle.prize_pool} coins`],
    ['Duration', `${battle.duration_minutes} min`],
    ['Started', formatDate(battle.start_time)],
    ['Ends', formatDate(battle.end_time)],
    [
      'Winner',
      battle.winner_id
        ? battle.winner_id === battle.challenger.user_id
          ? battle.challenger.username
          : battle.opponent.username
        : '—',
    ],
  ]

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">
          {battle.challenger.username} <span className="muted">vs</span> {battle.opponent.username}
        </h1>
        <Link className="btn btn-ghost btn-small" to="/competitions">← Back</Link>
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="detail-grid">
        <div className="card">
          <table className="table detail-table">
            <tbody>
              {rows.map(([label, value]) => (
                <tr key={label}>
                  <td className="muted">{label}</td>
                  <td>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-title">Participants</div>
          <table className="table detail-table">
            <tbody>
              <tr>
                <td className="muted">Challenger</td>
                <td>
                  <Link to={`/users/${battle.challenger.user_id}`}>{battle.challenger.username}</Link>
                  <div className="muted mono">{battle.challenger.user_id}</div>
                </td>
              </tr>
              <tr>
                <td className="muted">Opponent</td>
                <td>
                  <Link to={`/users/${battle.opponent.user_id}`}>{battle.opponent.username}</Link>
                  <div className="muted mono">{battle.opponent.user_id}</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Outfits</div>
        <div className="battle-outfits">
          <Outfit title={battle.challenger.username} avatar={battle.challenger_avatar} />
          <Outfit title={battle.opponent.username} avatar={battle.opponent_avatar} />
        </div>
      </div>
    </div>
  )
}

function Outfit({ title, avatar }) {
  const equipment = avatar?.equipment || {}
  const worn = SLOT_ORDER.map((slot) => [slot, equipment[slot]]).filter(([, entry]) => entry)

  return (
    <div>
      <div className="battle-outfit-title">{title}</div>
      {worn.length === 0 ? (
        <p className="battle-outfit-empty">Nothing equipped.</p>
      ) : (
        <div className="equipment-list">
          {worn.map(([slot, entry]) => (
            <div className="equipment-row" key={slot}>
              <span className="equipment-slot">{slot}</span>
              <img
                className="equipment-thumb"
                src={entry.item.image_url}
                alt=""
                onError={(event) => {
                  event.currentTarget.style.visibility = 'hidden'
                }}
              />
              <span>{entry.item.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
