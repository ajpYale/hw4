import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import { useLocation } from 'react-router-dom'
import type { ProductCardData } from '../api'
import { useAuth } from '../auth'
import ProductCard from './ProductCard'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  products?: ProductCardData[]
}

const GREETING: ChatMessage = {
  role: 'assistant',
  content:
    "Hey! I'm the Campus Customs shop assistant. Ask me what we carry, what something costs, or whether your size is in stock.",
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Page context, so "do you have this in pink?" can resolve "this" to whatever
  // product the shopper is looking at.
  //
  // Read from the path rather than useParams(): this widget is mounted outside
  // <Routes> so that it survives navigation, which means it has no route match of
  // its own and useParams() would always be empty.
  const { pathname } = useLocation()
  const productId = pathname.match(/^\/products\/(.+)$/)?.[1]
  const { user } = useAuth()

  // Reload a signed-in customer's past conversation. Guests start fresh every time.
  useEffect(() => {
    if (!user) {
      setMessages([GREETING])
      return
    }
    fetch('/api/chat/history')
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: { role: 'user' | 'assistant'; content: string; products: ProductCardData[] }[]) => {
        if (rows.length) {
          setMessages(rows.map((r) => ({ role: r.role, content: r.content, products: r.products })))
        } else {
          setMessages([GREETING])
        }
      })
      .catch(() => setMessages([GREETING]))
  }, [user])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, open])

  async function send(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || busy) return

    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setBusy(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          page_path: pathname,
          product_id: productId ?? null,
        }),
      })
      if (!res.ok) throw new Error(String(res.status))
      const data = await res.json()
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: data.reply_text, products: data.products ?? [] },
      ])
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content:
            "Sorry, I can't reach the shop assistant right now. Try again in a moment — browsing and product pages still work in the meantime.",
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button
        className="chat__launcher"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Close chat' : 'Open shop assistant chat'}
      >
        {open ? '×' : 'Chat'}
      </button>

      {open && (
        <section className="chat" aria-label="Shop assistant">
          <header className="chat__header">
            <span className="chat__dot" />
            Shop Assistant
          </header>

          <div className="chat__log" ref={scrollRef}>
            {messages.map((m, i) => (
              <div key={i} className={`bubble bubble--${m.role}`}>
                {m.role === 'assistant' ? (
                  <div className="bubble__md">
                    <Markdown>{m.content}</Markdown>
                  </div>
                ) : (
                  <p>{m.content}</p>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat__results">
                    {m.products.map((p) => (
                      <ProductCard key={p.product_id} product={p} compact />
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="bubble bubble--assistant">…</div>}
          </div>

          <form className="chat__form" onSubmit={send}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="What hoodies do you have?"
              aria-label="Message the shop assistant"
            />
            <button type="submit" disabled={busy || !input.trim()}>
              Send
            </button>
          </form>
        </section>
      )}
    </>
  )
}
