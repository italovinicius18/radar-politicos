import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { obterDespesas, obterResumo, type PaginaDespesas, type Resumo } from '../lib/api'
import { formatarBRL, formatarData } from '../lib/formato'

// Paleta dark validada (dataviz, superfície #11221a). Cores por RANK da fatia:
// a adjacência circular 1→…→6→1 é fixa; o pior par adjacente (10,3, faixa-piso)
// é coberto pelos vãos de 2px entre fatias + legenda.
const CORES_ROSCA = ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767']
const MAX_FATIAS = 5 // além disso, agrega em "Outras" (regra: >7 classes nunca)

export default function Perfil() {
  const { id } = useParams<{ id: string }>()
  const [resumo, setResumo] = useState<Resumo | null>(null)
  const [despesas, setDespesas] = useState<PaginaDespesas | null>(null)
  const [ano, setAno] = useState<number | undefined>()
  const [categoria, setCategoria] = useState('')
  const [pagina, setPagina] = useState(1)
  const [erro, setErro] = useState('')

  useEffect(() => {
    setResumo(null)
    setDespesas(null)
    setErro('')
    setAno(undefined)
    setCategoria('')
    setPagina(1)
    if (!id) return
    let ativo = true
    obterResumo(id)
      .then((r) => { if (ativo) setResumo(r) })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [id])

  useEffect(() => {
    if (!id) return
    let ativo = true
    obterDespesas(id, { ano, categoria: categoria || undefined, pagina, ordenar: '-data' })
      .then((d) => { if (ativo) setDespesas(d) })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [id, ano, categoria, pagina])

  if (erro) return <p className="cartao">⚠️ {erro}</p>
  if (!resumo) return <p>Carregando...</p>

  const { politico } = resumo
  const categoriasComGasto = resumo.por_categoria.filter((c) => c.total > 0)
  const fatias =
    categoriasComGasto.length <= MAX_FATIAS + 1
      ? categoriasComGasto
      : [
          ...categoriasComGasto.slice(0, MAX_FATIAS),
          {
            categoria: 'Outras (agregadas)',
            total: categoriasComGasto.slice(MAX_FATIAS).reduce((s, c) => s + c.total, 0),
          },
        ]
  const totalPaginas = despesas ? Math.max(1, Math.ceil(despesas.total_itens / despesas.por_pagina)) : 1

  return (
    <div>
      <div className="cartao resultado">
        {politico.foto_url && <img src={politico.foto_url} alt="" style={{ width: 72, height: 90 }} />}
        <div>
          <h1 style={{ margin: 0 }}>{politico.nome}</h1>
          <div>
            {politico.cargo}
            {politico.partido ? ` · ${politico.partido}` : ''}
            {politico.uf ? ` · ${politico.uf}` : ''}
          </div>
          <div className="total-destaque">{formatarBRL(resumo.total)}</div>
          <small>total no período disponível (estornos já descontados)</small>
        </div>
      </div>

      <div className="graficos">
        <div className="cartao">
          <h3>Gasto por ano</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={resumo.por_ano}>
              <XAxis dataKey="ano" />
              <YAxis tickFormatter={(v) => `${Math.round(v / 1000)}k`} width={50} />
              <Tooltip formatter={(v) => formatarBRL(Number(v))} />
              <Bar dataKey="total" fill="#199e70" radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="cartao">
          <h3>Por categoria (o porquê)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={fatias}
                dataKey="total"
                nameKey="categoria"
                innerRadius={50}
                outerRadius={90}
                paddingAngle={2}
                stroke="#11221a"
              >
                {fatias.map((c, i) => (
                  <Cell key={c.categoria} fill={CORES_ROSCA[i % CORES_ROSCA.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatarBRL(Number(v))} />
              <Legend formatter={(valor) => <span style={{ color: '#d7e4da' }}>{valor}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="cartao">
        <h3>Top fornecedores (para quem foi o dinheiro)</h3>
        <table>
          <thead>
            <tr><th>Fornecedor</th><th>CNPJ/CPF</th><th>Notas</th><th className="valor">Total</th></tr>
          </thead>
          <tbody>
            {resumo.top_fornecedores.map((f) => (
              <tr key={f.fornecedor + f.cnpj}>
                <td>{f.fornecedor}</td>
                <td>{f.cnpj || '—'}</td>
                <td>{f.quantidade}</td>
                <td className="valor">{formatarBRL(f.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="cartao">
        <h3>Despesas</h3>
        <div className="filtros">
          <select value={ano ?? ''} onChange={(e) => { setPagina(1); setAno(e.target.value ? Number(e.target.value) : undefined) }}>
            <option value="">Todos os anos</option>
            {resumo.por_ano.map((a) => <option key={a.ano} value={a.ano}>{a.ano}</option>)}
          </select>
          <select value={categoria} onChange={(e) => { setPagina(1); setCategoria(e.target.value) }}>
            <option value="">Todas as categorias</option>
            {resumo.por_categoria.map((c) => (
              <option key={c.categoria} value={c.categoria}>{c.categoria}</option>
            ))}
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Data</th><th>Categoria</th><th>Fornecedor</th><th>Detalhe</th>
              <th className="valor">Valor</th><th>Nota</th>
            </tr>
          </thead>
          <tbody>
            {despesas?.itens.map((d, i) => (
              <tr key={i}>
                <td>{d.data ? formatarData(d.data) : `${d.mes ?? '—'}/${d.ano}`}</td>
                <td title={d.categoria_original}>{d.categoria}</td>
                <td>{d.fornecedor ?? '—'}</td>
                <td>{d.descricao ?? '—'}</td>
                <td className="valor">{formatarBRL(d.valor)}</td>
                <td>
                  {d.documento_url
                    ? <a href={d.documento_url} target="_blank" rel="noreferrer">📄</a>
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="paginacao">
          <button disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>← Anterior</button>
          <span>Página {pagina} de {totalPaginas} ({despesas?.total_itens ?? 0} despesas)</span>
          <button disabled={pagina >= totalPaginas} onClick={() => setPagina(pagina + 1)}>Próxima →</button>
        </div>
      </div>
    </div>
  )
}
