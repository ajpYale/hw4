import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function CreateAccount() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password !== form.confirm) {
      setError('Those passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const { confirm, ...data } = form
      void confirm
      await register(data)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="section auth">
      <p className="eyebrow">Join Campus Customs</p>
      <h1>Create account</h1>

      <form onSubmit={submit} className="form">
        <div className="form__pair">
          <label>
            First name
            <input value={form.first_name} onChange={set('first_name')} required />
          </label>
          <label>
            Last name
            <input value={form.last_name} onChange={set('last_name')} required />
          </label>
        </div>

        <label>
          Email
          <input
            type="email"
            value={form.email}
            onChange={set('email')}
            required
            autoComplete="email"
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={form.password}
            onChange={set('password')}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>

        <label>
          Confirm password
          <input
            type="password"
            value={form.confirm}
            onChange={set('confirm')}
            required
            autoComplete="new-password"
          />
        </label>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="btn btn--wide" disabled={busy}>
          {busy ? 'Creating…' : 'Create account'}
        </button>
      </form>

      <p className="muted">
        Already have one? <Link to="/login">Log in</Link>.
      </p>
    </section>
  )
}
