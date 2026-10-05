import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  async function signOut() {
    await logout()
    navigate('/')
  }

  return (
    <header className="nav">
      <div className="nav__inner">
        <NavLink to="/" className="nav__brand">
          Campus<span>Customs</span>
        </NavLink>

        <nav className="nav__links">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                isActive ? 'nav__link nav__link--active' : 'nav__link'
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="nav__auth">
          {loading ? null : user ? (
            <>
              <span className="nav__who">Hi, {user.first_name}</span>
              <button className="nav__link nav__link--button" onClick={signOut}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="nav__link">
                Log in
              </NavLink>
              <NavLink to="/create-account" className="btn btn--small">
                Create account
              </NavLink>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
