import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { buscarPoliticos, type Politico } from '../lib/api'
import Panorama from './Panorama'

export default function Busca() {
  const [busca, setBusca] = useState('')
  const [resultados, setResultados] = useState<Politico[]>([])
  const [erro, setErro] = useState('')

  useEffect(() => {
    if (busca.trim().length < 3) { setResultados([]); setErro(''); return }
    let ativo = true
    const timer = setTimeout(() => {
      buscarPoliticos(busca)
        .then((r) => { if (ativo) { setResultados(r); setErro('') } })
        .catch((e) => { if (ativo) setErro(e.message) })
    }, 300)
    return () => { ativo = false; clearTimeout(timer) }
  }, [busca])

  return (
    <div>
      <h1>Buscar político</h1>
      <input
        className="busca-input"
        placeholder="Digite o nome (mín. 3 letras) — ex: Nikolas, Alan Rick..."
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        autoFocus
      />
      {erro && <p className="cartao">⚠️ {erro}</p>}
      {resultados.map((p) => (
        <Link key={p.id} to={`/politico/${p.id}`}>
          <div className="cartao resultado">
            {p.foto_url ? <img src={p.foto_url} alt="" /> : <div style={{ width: 48 }} />}
            <div>
              <strong>{p.nome}</strong>
              <div>
                {p.cargo}
                {p.partido ? ` · ${p.partido}` : ''}
                {p.uf ? ` · ${p.uf}` : ''}
              </div>
            </div>
          </div>
        </Link>
      ))}
      {busca.trim().length >= 3 && resultados.length === 0 && !erro && (
        <p>Nenhum político encontrado.</p>
      )}
      {busca.trim().length < 3 && <Panorama />}
    </div>
  )
}
