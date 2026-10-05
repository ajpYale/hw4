export type SizeStock = { size: string; quantity: number }

export type ProductCardData = {
  product_id: string
  name: string
  garment_type: string
  category: string
  price: number
  image_url: string
  colors: string[]
  blurb: string
  in_stock_sizes: string[]
}

export type ProductDetailData = ProductCardData & {
  description: string
  search_tags: string[]
  sizes: SizeStock[]
}

export type Category = { name: string; count: number }

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`)
  return res.json() as Promise<T>
}

export function fetchCategories() {
  return get<Category[]>('/api/categories')
}

export function fetchProducts(category?: string, q?: string) {
  const params = new URLSearchParams()
  if (category && category !== 'All') params.set('category', category)
  if (q) params.set('q', q)
  const qs = params.toString()
  return get<ProductCardData[]>(`/api/products${qs ? `?${qs}` : ''}`)
}

export function fetchProduct(productId: string) {
  return get<ProductDetailData>(`/api/products/${productId}`)
}

export const money = (n: number) => `$${n.toFixed(2).replace(/\.00$/, '')}`
