import { useEffect, useState } from 'react'
import { api, saveFile } from '../api'
import { ErrorBanner } from './ui'

const PER_PAGE_OPTIONS = [
  { value: 20, label: '20 per page (4 × 5)' },
  { value: 1, label: '1 per page (large)' },
  { value: 4, label: '4 per page' },
  { value: 6, label: '6 per page' },
  { value: 12, label: '12 per page' },
  { value: 24, label: '24 per page' },
  { value: 35, label: '35 per page' },
]

// Creates many QR codes at once and downloads a printable PDF. The codes
// are saved only if the PDF was built, so nothing is created and then lost.
export default function BatchQrModal({ onCreated, onClose }) {
  const [products, setProducts] = useState([])
  const [productId, setProductId] = useState('')
  const [coinValue, setCoinValue] = useState('')
  const [count, setCount] = useState('100')
  const [perPage, setPerPage] = useState(20)
  const [expiresAt, setExpiresAt] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [loadingProducts, setLoadingProducts] = useState(true)

  useEffect(() => {
    api
      .products()
      .then((data) => {
        setProducts(data.items)
        if (data.items.length > 0) setProductId((current) => current || data.items[0].product_id)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoadingProducts(false))
  }, [])

  const pages = Math.ceil((Number(count) || 0) / perPage)

  const submit = async (event) => {
    event.preventDefault()
    setError(null)
    if (!productId) {
      setError('Please select a product first.')
      return
    }
    setSubmitting(true)
    try {
      const body = {
        product_id: productId,
        coin_value: Number(coinValue),
        count: Number(count),
        per_page: perPage,
      }
      if (expiresAt) body.expires_at = new Date(expiresAt).toISOString()
      const { blob, count: created } = await api.createQrBatch(body)
      saveFile(blob, `qr-codes-${created}.pdf`)
      onCreated(created)
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Generate QR codes for printing</h2>
          <button className="btn btn-ghost btn-small" onClick={onClose}>
            ×
          </button>
        </div>
        <ErrorBanner message={error} />
        <form onSubmit={submit}>
          <label className="field">
            <span>Product</span>
            <select
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              required
              disabled={loadingProducts || products.length === 0}
            >
              {loadingProducts && <option value="">Loading products…</option>}
              {!loadingProducts && products.length === 0 && (
                <option value="">No products available</option>
              )}
              {products.map((p) => (
                <option key={p.product_id} value={p.product_id}>
                  {p.name} ({p.sku})
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Coins per code</span>
            <input
              type="number"
              min="1"
              step="1"
              value={coinValue}
              onChange={(e) => setCoinValue(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>How many codes (1–2000)</span>
            <input
              type="number"
              min="1"
              max="2000"
              step="1"
              value={count}
              onChange={(e) => setCount(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Codes per page</span>
            <select value={perPage} onChange={(e) => setPerPage(Number(e.target.value))}>
              {PER_PAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {pages > 0 && <small className="field-hint">{pages} page(s) of A4</small>}
          </label>
          <label className="field">
            <span>Expiration (optional)</span>
            <input
              type="datetime-local"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
            />
          </label>
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || loadingProducts || products.length === 0}
            >
              {submitting ? 'Generating…' : 'Generate PDF'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
