import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { obterVisaoGeral, type VisaoGeral } from '../lib/api'
import { formatarBRL, formatarBRLCompacto, MESES_ABREV } from '../lib/formato'
import { infoFonte } from '../lib/fontes'

const ANOS = Array.from({ length: 14 }, (_, i) => 2013 + i)
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
  const e = dados.estatisticas
  const maxUf = dados.media_por_uf[0]?.media ?? 0

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

      <div className="tiles">
        <div className="cartao tile">
          <small>Efeito fim de ano</small>
          <div className="tile-valor">
            {e.fim_de_ano
              ? `${e.fim_de_ano.variacao_pct >= 0 ? '+' : ''}${e.fim_de_ano.variacao_pct.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
              : '—'}
          </div>
          <small>
            {e.fim_de_ano
              ? `dez/${e.fim_de_ano.ano_ref} vs média mensal (${formatarBRLCompacto(e.fim_de_ano.media_mensal)})`
              : 'sem dezembro na base'}
          </small>
        </div>
        <div className="cartao tile">
          <small>Despesas com nota anexada</small>
          <div className="tile-valor">
            {e.transparencia
              ? `${e.transparencia.pct_com_documento.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
              : '—'}
          </div>
          <small>
            {e.transparencia
              ? e.transparencia.por_fonte.map((f) => `${f.rotulo}: ${f.pct.toFixed(0)}%`).join(' · ')
              : 'sem dados no ano'}
          </small>
        </div>
        <div className="cartao tile">
          <small>Concentração de fornecedores</small>
          <div className="tile-valor">
            {e.concentracao_top10_pct !== null
              ? `${e.concentracao_top10_pct.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`
              : '—'}
          </div>
          <small>do gasto do ano vai para os 10 maiores fornecedores</small>
        </div>
        <div className="cartao tile">
          <small>Fornecedores quase-exclusivos</small>
          <div className="tile-valor">{e.quase_exclusivos.quantidade}</div>
          <small>
            ≥ R$ 50 mil no ano com ≥ 90% de um só parlamentar
            {e.quase_exclusivos.maior && (
              <>
                {' — maior: '}{e.quase_exclusivos.maior.fornecedor} ({formatarBRLCompacto(e.quase_exclusivos.maior.total)},{' '}
                {e.quase_exclusivos.maior.pct_um_parlamentar.toFixed(0)}% de{' '}
                <Link to={`/politico/${e.quase_exclusivos.maior.politico.id}`}>{e.quase_exclusivos.maior.politico.nome}</Link>)
              </>
            )}
          </small>
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
                <span className="leader" aria-hidden="true" />
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
              <span className="leader" aria-hidden="true" />
              <span className="top-valor">{formatarBRLCompacto(f.total)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="graficos">
        <div className="cartao">
          <h3>Gasto por partido (por parlamentar)</h3>
          <div className="tabela-rolavel">
            <table className="tabela-compacta">
              <thead>
                <tr><th>Partido</th><th>Parl.</th><th className="valor">Mediana</th><th className="valor">Média</th></tr>
              </thead>
              <tbody>
                {dados.por_partido.map((p) => (
                  <tr key={p.partido}>
                    <td>{p.partido}</td>
                    <td>{p.parlamentares}</td>
                    <td className="valor">{formatarBRLCompacto(p.mediana)}</td>
                    <td className="valor">{formatarBRLCompacto(p.media)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <small className="rodape-nota">Média longe da mediana indica gastador extremo puxando o partido para cima.</small>
        </div>
        <div className="cartao">
          <h3>Média por estado (por parlamentar)</h3>
          <div className="tabela-rolavel">
            {dados.media_por_uf.map((u) => (
              <div key={u.uf} className="minibar-linha">
                <div className="minibar-rotulo">
                  <span>{u.uf} <small>({u.parlamentares})</small></span>
                  <span className="top-valor">{formatarBRLCompacto(u.media)}</span>
                </div>
                <div className="minibar-trilha">
                  <div className="minibar" style={{ width: maxUf ? `${(u.media / maxUf) * 100}%` : 0 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="cartao">
        <h3>Por casa (média e mediana por parlamentar)</h3>
        <table className="tabela-compacta">
          <thead>
            <tr><th>Casa</th><th>Parlamentares</th><th className="valor">Mediana</th><th className="valor">Média</th></tr>
          </thead>
          <tbody>
            {dados.por_casa.map((x) => (
              <tr key={x.fonte}>
                <td>{x.rotulo}</td>
                <td>{x.parlamentares}</td>
                <td className="valor">{formatarBRLCompacto(x.mediana)}</td>
                <td className="valor">{formatarBRLCompacto(x.media)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <small className="rodape-nota">Os tetos de cota diferem por casa — compare parlamentares dentro da mesma casa.</small>
      </div>
    </section>
  )
}
