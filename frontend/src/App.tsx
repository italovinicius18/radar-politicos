import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Busca from './paginas/Busca'
import Perfil from './paginas/Perfil'
import Rankings from './paginas/Rankings'

export default function App() {
  return (
    <BrowserRouter>
      <header className="cabecalho">
        <div className="container">
          <Link to="/" className="wordmark"><span>▸</span>Radar Políticos</Link>
          <nav>
            <Link to="/rankings">Rankings</Link>
          </nav>
        </div>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<Busca />} />
          <Route path="/politico/:id" element={<Perfil />} />
          <Route path="/rankings" element={<Rankings />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
