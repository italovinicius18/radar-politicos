import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { obterVisaoGeral, type VisaoGeral } from '../lib/api'
import { formatarBRL, formatarBRLCompacto, MESES_ABREV } from '../lib/formato'
import { infoFonte } from '../lib/fontes'

const ANOS = Array.from({ length: 11 }, (_, i) => 2016 + i)
// Cores validadas (dataviz): verde de marca de gráfico
const COR_MARCA = '#1d7a4d'

export default function Panorama() {
  const [dados, setDados] = useState<VisaoGeral | null>(null)
  const [ano, setAno] = useState<number | undefined>()
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    obterVisaoGeral(ano)
      .then((d) => { if (ativo) { setDados(d); setErro('') } })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [ano])

  if (erro) return <p className="cartao">⚠️ Panorama indisponível: {erro}</p>
  if (!dados) return <p>Carregando panorama...</p>

  const { kpis } = dados
  const nota = kpis.nota_mais_cara
  const totalCasas = dados.por_casa.reduce((s, x) => s + x.total, 0)
  const serieMensal = dados.por_mes.map((m) => ({ nome: MESES_ABREV[m.mes - 1], total: m.total }))
  const maxCategoria = dados.top_categorias[0]?.total ?? 0

  return (
    <section>
      <div className="panorama-titulo">
        <h2>Panorama</h2>
        <select value={dados.ano} onChange={(e) => setAno(Number(e.target.value))}>
          {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      <div className="tiles">
        <div className="cartao tile">
          <small>Total gasto em {dados.ano}</small>
          <div className="tile-valor">{formatarBRLCompacto(kpis.total)}</div>
          {kpis.variacao_pct !== null && (
            <small>
              {kpis.variacao_pct >= 0 ? '▲' : '▼'} {Math.abs(kpis.variacao_pct).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%
              {' '}vs jan–{MESES_ABREV[kpis.meses_com_dados - 1]}/{dados.ano - 1}
            </small>
          )}
        </div>
        <div className="cartao tile">
          <small>Parlamentares com gastos</small>
          <div className="tile-valor">{kpis.parlamentares}</div>
          <small>{kpis.por_cargo.map((c) => `${c.cargo}: ${c.quantidade}`).join(' · ')}</small>
        </div>
        <div className="cartao tile">
          <small>Média por parlamentar</small>
          <div className="tile-valor">{formatarBRLCompacto(kpis.media_por_parlamentar)}</div>
          <small>{kpis.num_despesas.toLocaleString('pt-BR')} despesas no ano</small>
        </div>
        <div className="cartao tile">
          <small>Nota mais cara do ano</small>
          <div className="tile-valor">{nota ? formatarBRLCompacto(nota.valor) : '—'}</div>
          {nota && (
            <small>
              <Link to={`/politico/${nota.politico.id}`}>{nota.politico.nome}</Link> · {nota.categoria}
            </small>
          )}
        </div>
      </div>

      <div className="graficos">
        <div className="cartao">
          <h3>Gasto mês a mês</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={serieMensal}>
              <XAxis dataKey="nome" tickLine={false} axisLine={false} />
              <YAxis tickFormatter={(v) => formatarBRLCompacto(Number(v))} width={80}
                     tickLine={false} axisLine={false} />
              <Tooltip formatter={(v) => formatarBRL(Number(v))} />
              <Bar dataKey="total" name="Total" fill={COR_MARCA} radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="cartao">
          <h3>Por casa</h3>
          <div className="split-bar">
            {dados.por_casa.map((x) => (
              <div
                key={x.fonte}
                className="split-parte"
                style={{
                  width: totalCasas ? `${(x.total / totalCasas) * 100}%` : `${100 / dados.por_casa.length}%`,
                  background: infoFonte(x.fonte).cor,
                }}
              />
            ))}
          </div>
          {dados.por_casa.map((x) => (
            <div key={x.fonte} className="split-legenda">
              <span className="pino" style={{ background: infoFonte(x.fonte).cor }} />
              {x.rotulo}: {formatarBRLCompacto(x.total)}
              {' '}({x.parlamentares} parlamentares{totalCasas ? `, ${((x.total / totalCasas) * 100).toFixed(0)}%` : ''})
            </div>
          ))}
        </div>
      </div>

      <div className="tops">
        <div className="cartao">
          <h3>Top 5 gastadores</h3>
          {dados.top_gastadores.map((g, i) => (
            <Link key={g.politico.id} to={`/politico/${g.politico.id}`}>
              <div className="top-linha">
                <span className="top-posicao">{i + 1}º</span>
                {g.politico.foto_url && <img src={g.politico.foto_url} alt="" />}
                <span className="top-nome">
                  {g.politico.nome}
                  <small>{[g.politico.partido, g.politico.uf].filter(Boolean).join('/')}</small>
                </span>
                <span className="top-valor">{formatarBRLCompacto(g.total)}</span>
              </div>
            </Link>
          ))}
        </div>
        <div className="cartao">
          <h3>Top 5 categorias</h3>
          {dados.top_categorias.map((c) => (
            <div key={c.categoria} className="minibar-linha">
              <div className="minibar-rotulo">
                <span>{c.categoria}</span>
                <span className="top-valor">{formatarBRLCompacto(c.total)}</span>
              </div>
              <div className="minibar-trilha">
                <div className="minibar" style={{ width: maxCategoria ? `${(c.total / maxCategoria) * 100}%` : 0 }} />
              </div>
            </div>
          ))}
        </div>
        <div className="cartao">
          <h3>Top 5 fornecedores</h3>
          {dados.top_fornecedores.map((f) => (
            <div key={f.fornecedor + f.cnpj} className="top-linha">
              <span className="top-nome">
                {f.fornecedor}
                <small>{f.cnpj || '—'} · {f.quantidade} notas</small>
              </span>
              <span className="top-valor">{formatarBRLCompacto(f.total)}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
