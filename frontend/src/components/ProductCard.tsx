import { Link } from 'react-router-dom'
import type { ProductCardData } from '../api'
import { money } from '../api'

// Used by both the Products grid and the chat widget's results. Problem 7 requires
// chat-injected cards to open the same detail page as browsed ones, so there is
// deliberately only one card component and one link target.
export default function ProductCard({
  product,
  compact = false,
}: {
  product: ProductCardData
  compact?: boolean
}) {
  // Availability is shown on the card so a shopper learns their size is gone before
  // clicking through, rather than after.
  const sizes = product.in_stock_sizes ?? []
  const soldOut = sizes.length === 0
  const limited = !soldOut && sizes.length <= 3

  return (
    <Link
      to={`/products/${product.product_id}`}
      className={compact ? 'card card--compact' : 'card'}
    >
      <div className="card__image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {soldOut && <span className="badge badge--out">Sold out</span>}
        {limited && <span className="badge badge--low">Only {sizes.join(', ')}</span>}
      </div>
      <div className="card__body">
        <h3 className="card__name">{product.name}</h3>
        <p className="card__meta">{product.category}</p>
        {!compact && <p className="card__blurb">{product.blurb}</p>}
        <p className="card__price">{money(product.price)}</p>
      </div>
    </Link>
  )
}
