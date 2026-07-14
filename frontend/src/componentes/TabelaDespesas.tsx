'use client'
import { useEffect, useMemo, useState } from 'react'
import type { DespesasCompactas } from '@/lib/tipos'
import { formatarBRL, formatarData } from '@/lib/formato'

const POR_PAGINA = 50

interface Linha {
  ano: number; data: string | null; categoria: string; categoria_original: string
  descricao: string | null; fornecedor: string | null; cnpj: string | null
  valor: number; doc: string | null
}

export function TabelaDespesas({ politicoId, anos, categorias }:
  { politicoId: string; anos: number[]; categorias: string[] }) {
  const [ano, setAno] = useState(Math.max(...anos))
  const [linhas, setLinhas] = useState<Linha[] | null>(null)
  const [categoria, setCategoria] = useState('')
  const [ordenar, setOrdenar] = useState<'-data' | '-valor'>('-data')
  const [pagina, setPagina] = useState(1)
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    setLinhas(null)
    fetch(`/dados/despesas/${politicoId}.json`)
      .then((r) => { if (!r.ok) throw new Error(`Erro ${r.status}`); return r.json() })
      .then((d: DespesasCompactas) => {
        if (!ativo) return
        setLinhas(d.linhas.map((l) => ({
          ano: l[0] as number, data: l[1] as string | null, categoria: l[2] as string,
          categoria_original: l[3] as string, descricao: l[4] as string | null,
          fornecedor: l[5] as string | null, cnpj: l[6] as string | null,
          valor: l[7] as number, doc: l[8] as string | null,
        })))
        setErro('')
      })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [politicoId])

  const filtradas = useMemo(() => {
    let base = linhas ?? []
    base = base.filter((l) => l.ano === ano)
    if (categoria) base = base.filter((l) => l.categoria === categoria)
    if (ordenar === '-valor') base = [...base].sort((a, b) => b.valor - a.valor)
    return base
  }, [linhas, ano, categoria, ordenar])

  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / POR_PAGINA))
  const visiveis = filtradas.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA)

  return (
    <div className="cartao">
      <h3>Despesas</h3>
      <div className="filtros">
        <select value={ano} onChange={(e) => { setPagina(1); setAno(Number(e.target.value)) }}>
          {[...anos].sort((a, b) => b - a).map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <select value={categoria} onChange={(e) => { setPagina(1); setCategoria(e.target.value) }}>
          <option value="">Todas as categorias</option>
          {categorias.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={ordenar} onChange={(e) => { setPagina(1); setOrdenar(e.target.value as '-data' | '-valor') }}>
          <option value="-data">Mais recentes</option>
          <option value="-valor">Maior valor</option>
        </select>
      </div>
      {erro && <p>⚠️ {erro}</p>}
      {!linhas && !erro && <p>Carregando despesas...</p>}
      <table>
        <thead>
          <tr>
            <th>Data</th><th>Categoria</th><th>Fornecedor</th><th>Detalhe</th>
            <th className="valor">Valor</th><th>Nota</th>
          </tr>
        </thead>
        <tbody>
          {visiveis.map((d, i) => (
            <tr key={i}>
              <td>{d.data ? formatarData(d.data) : '—'}</td>
              <td title={d.categoria_original}>{d.categoria}</td>
              <td>{d.fornecedor ?? '—'}</td>
              <td>{d.descricao ?? '—'}</td>
              <td className="valor">{formatarBRL(d.valor)}</td>
              <td>{d.doc ? <a href={d.doc} target="_blank" rel="noreferrer">📄</a> : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="paginacao">
        <button disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>← Anterior</button>
        <span>Página {pagina} de {totalPaginas} ({filtradas.length} despesas em {ano})</span>
        <button disabled={pagina >= totalPaginas} onClick={() => setPagina(pagina + 1)}>Próxima →</button>
      </div>
    </div>
  )
}
