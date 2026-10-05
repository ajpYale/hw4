import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, money } from '../api'
import type { ProductDetailData } from '../api'

export default function ProductDetail() {
  const { productId } = useParams()
  const [product, setProduct] = useState<ProductDetailData | null>(null)
  const [error, setError] = useState(false)
  const [size, setSize] = useState<string | null>(null)

  useEffect(() => {
    if (!productId) return
    setProduct(null)
    setError(false)
    setSize(null)
    fetchProduct(productId).then(setProduct).catch(() => setError(true))
  }, [productId])

  if (error) {
    return (
      <section className="section">
        <h1>We could not find that one.</h1>
        <Link to="/products" className="btn">
          Back to the collection
        </Link>
      </section>
    )
  }

  if (!product) return <p className="section muted">Loading…</p>

  const selected = product.sizes.find((s) => s.size === size)
  const soldOut = product.sizes.every((s) => s.quantity === 0)

  return (
    <section className="section detail">
      <div className="detail__media">
        <img src={product.image_url} alt={product.name} />
      </div>

      <div className="detail__info">
        <p className="eyebrow">{product.category}</p>
        <h1>{product.name}</h1>
        <p className="detail__price">{money(product.price)}</p>
        <p className="detail__desc">{product.description}</p>

        <div className="detail__row">
          <span className="label">Colors</span>
          <div className="pills">
            {product.colors.map((c) => (
              <span key={c} className="pill">
                {c}
              </span>
            ))}
          </div>
        </div>

        <div className="detail__row">
          <span className="label">Size</span>
          <div className="sizes">
            {product.sizes.map((s) => (
              <button
                key={s.size}
                disabled={s.quantity === 0}
                className={
                  size === s.size ? 'size size--active' : s.quantity === 0 ? 'size size--out' : 'size'
                }
                onClick={() => setSize(s.size)}
                title={s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}
              >
                {s.size}
              </button>
            ))}
          </div>
        </div>

        <p className="stock">
          {soldOut
            ? 'Sold out in every size right now.'
            : selected
              ? `${selected.quantity} left in ${selected.size}.`
              : 'Pick a size to see what is left.'}
        </p>

        <button className="btn btn--wide" disabled={!selected}>
          {selected ? `Add ${selected.size} to bag` : 'Select a size'}
        </button>

        <div className="detail__row">
          <span className="label">Tags</span>
          <div className="pills">
            {product.search_tags.map((t) => (
              <span key={t} className="pill pill--quiet">
                {t}
              </span>
            ))}
          </div>
        </div>

        <Link to="/products" className="backlink">
          ← Back to the collection
        </Link>
      </div>
    </section>
  )
}
