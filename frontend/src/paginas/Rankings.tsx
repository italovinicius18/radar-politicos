import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { obterRankings, type ItemRanking } from '../lib/api'
import { formatarBRL } from '../lib/formato'

const ANOS = Array.from({ length: 11 }, (_, i) => 2016 + i)

export default function Rankings() {
  const [ano, setAno] = useState<number | undefined>(2026)
  const [cargo, setCargo] = useState('')
  const [itens, setItens] = useState<ItemRanking[]>([])
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    obterRankings({ ano, cargo: cargo || undefined })
      .then((r) => { if (ativo) { setItens(r); setErro('') } })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [ano, cargo])

  return (
    <div>
      <h1>Rankings — quem mais gastou</h1>
      <div className="filtros">
        <select value={ano ?? ''} onChange={(e) => setAno(e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">Todos os anos</option>
          {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select value={cargo} onChange={(e) => setCargo(e.target.value)}>
          <option value="">Todos os cargos</option>
          <option value="Deputado Federal">Deputados Federais</option>
          <option value="Senador">Senadores</option>
        </select>
      </div>
      {erro && <p className="cartao">⚠️ {erro}</p>}
      <div className="cartao">
        <table>
          <thead>
            <tr><th>#</th><th>Político</th><th>Cargo</th><th>Partido/UF</th><th className="valor">Total</th></tr>
          </thead>
          <tbody>
            {itens.map((item, i) => (
              <tr key={item.politico.id}>
                <td>{i + 1}º</td>
                <td><Link to={`/politico/${item.politico.id}`}>{item.politico.nome}</Link></td>
                <td>{item.politico.cargo}</td>
                <td>{[item.politico.partido, item.politico.uf].filter(Boolean).join('/') || '—'}</td>
                <td className="valor">{formatarBRL(item.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
