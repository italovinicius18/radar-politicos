import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Busca from './paginas/Busca'
import Perfil from './paginas/Perfil'
import Rankings from './paginas/Rankings'

export default function App() {
  return (
    <BrowserRouter>
      <header className="cabecalho">
        <div className="container">
          <Link to="/" className="wordmark"><span>⦿</span>Radar Políticos</Link>
          <nav>
            <Link to="/rankings">Rankings</Link>
          </nav>
          <span className="status-base">
            base: <b>3 casas</b> · Câmara · Senado · CLDF · <b>2013–2026</b>
          </span>
        </div>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<Busca />} />
          <Route path="/politico/:id" element={<Perfil />} />
          <Route path="/rankings" element={<Rankings />} />
        </Routes>
      </main>
      <footer className="rodape">
        <div className="container">
          <strong>O Radar Políticos não tem vínculo nem viés político-partidário.</strong>{' '}
          Todos os dados vêm das bases abertas oficiais — Câmara dos Deputados (CEAP), Senado
          Federal (CEAPS) e Câmara Legislativa do DF — e são apresentados como publicados, sem
          edição. O objetivo é dar ao cidadão acesso claro à informação que já é pública.
        </div>
      </footer>
    </BrowserRouter>
  )
}
