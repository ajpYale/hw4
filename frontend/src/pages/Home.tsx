import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchCategories, fetchProducts } from '../api'
import type { Category, ProductCardData } from '../api'
import ProductCard from '../components/ProductCard'

export default function Home() {
  const [featured, setFeatured] = useState<ProductCardData[]>([])
  const [categories, setCategories] = useState<Category[]>([])

  useEffect(() => {
    fetchProducts().then((all) => setFeatured(all.slice(0, 4))).catch(() => {})
    fetchCategories().then(setCategories).catch(() => {})
  }, [])

  return (
    <>
      <section className="hero">
        <div className="hero__text">
          <p className="eyebrow">New Haven, Connecticut</p>
          <h1>Wear the whole four years.</h1>
          <p className="hero__lede">
            Campus Customs makes Yale gear built for the walk across Cross Campus in
            February, not just for move-in photos. Heavyweight fleece, honest stitching,
            and a fit that survives the laundry room in the basement of your entryway.
          </p>
          <div className="hero__actions">
            <Link to="/products" className="btn">
              Shop the collection
            </Link>
            <Link to="/about" className="btn btn--ghost">
              Our story
            </Link>
          </div>
        </div>
      </section>

      {categories.length > 0 && (
        <section className="section">
          <h2 className="section__title">Shop by category</h2>
          <div className="chips">
            {categories.map((c) => (
              <Link key={c.name} to={`/products?category=${encodeURIComponent(c.name)}`} className="chip">
                {c.name} <span>{c.count}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="section">
        <h2 className="section__title">Fresh off the press</h2>
        <div className="grid">
          {featured.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="section band">
        <div className="band__item">
          <h3>Printed in New Haven</h3>
          <p>Every order runs through our shop on Chapel Street. Nothing is drop-shipped.</p>
        </div>
        <div className="band__item">
          <h3>Sized for real people</h3>
          <p>XS through XXL on every design, with live stock counts so nothing is a surprise.</p>
        </div>
        <div className="band__item">
          <h3>Ask before you buy</h3>
          <p>Our shop assistant knows the catalogue and will tell you when a size is gone.</p>
        </div>
      </section>
    </>
  )
}
