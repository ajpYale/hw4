import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchCategories, fetchProducts } from '../api'
import type { Category, ProductCardData } from '../api'
import ProductCard from '../components/ProductCard'

export default function Products() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') ?? 'All'
  const query = params.get('q') ?? ''

  const [products, setProducts] = useState<ProductCardData[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState(query)

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchProducts(category, query)
      .then(setProducts)
      .catch(() => setProducts([]))
      .finally(() => setLoading(false))
  }, [category, query])

  function pick(name: string) {
    const next = new URLSearchParams(params)
    if (name === 'All') next.delete('category')
    else next.set('category', name)
    setParams(next)
  }

  function submitSearch(e: React.FormEvent) {
    e.preventDefault()
    const next = new URLSearchParams(params)
    if (search.trim()) next.set('q', search.trim())
    else next.delete('q')
    setParams(next)
  }

  const total = categories.reduce((sum, c) => sum + c.count, 0)

  return (
    <section className="section">
      <p className="eyebrow">Products</p>
      <h1>The collection</h1>

      <div className="toolbar">
        <div className="chips">
          <button
            className={category === 'All' ? 'chip chip--active' : 'chip'}
            onClick={() => pick('All')}
          >
            All <span>{total}</span>
          </button>
          {categories.map((c) => (
            <button
              key={c.name}
              className={category === c.name ? 'chip chip--active' : 'chip'}
              onClick={() => pick(c.name)}
            >
              {c.name} <span>{c.count}</span>
            </button>
          ))}
        </div>

        <form className="search" onSubmit={submitSearch}>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search colors, tags, designs…"
            aria-label="Search products"
          />
          <button type="submit">Search</button>
        </form>
      </div>

      {loading ? (
        <p className="muted">Loading the catalogue…</p>
      ) : products.length === 0 ? (
        <p className="muted">Nothing matched that. Try a broader search.</p>
      ) : (
        <>
          <p className="muted">
            {products.length} {products.length === 1 ? 'item' : 'items'}
          </p>
          <div className="grid">
            {products.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
