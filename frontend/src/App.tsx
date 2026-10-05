import { Route, Routes } from 'react-router-dom'
import ChatWidget from './components/ChatWidget'
import NavBar from './components/NavBar'
import About from './pages/About'
import CreateAccount from './pages/CreateAccount'
import Home from './pages/Home'
import Login from './pages/Login'
import ProductDetail from './pages/ProductDetail'
import Products from './pages/Products'

export default function App() {
  return (
    <div className="app">
      <NavBar />

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
        </Routes>
      </main>

      <footer className="footer">
        <span>Campus Customs · Chapel Street, New Haven</span>
        <span className="muted">MGT 409 coursework</span>
      </footer>

      <ChatWidget />
    </div>
  )
}
