'use client'
import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import type { RankingsAno } from '@/lib/tipos'
import { formatarBRL } from '@/lib/formato'

export function Rankings({ anos, anoInicial, dadosIniciais }: {
  anos: number[]
  anoInicial: number
  dadosIniciais: RankingsAno
}) {
  const [ano, setAno] = useState<number | undefined>(anoInicial)
  const [cargo, setCargo] = useState('')
  const [dados, setDados] = useState<RankingsAno>(dadosIniciais)
  const [erro, setErro] = useState('')
  const primeiraRenderizacao = useRef(true)

  useEffect(() => {
    if (primeiraRenderizacao.current) {
      primeiraRenderizacao.current = false
      return
    }
    let ativo = true
    fetch(`/dados/rankings/${ano ?? 'todos'}.json`)
      .then((r) => { if (!r.ok) throw new Error(`Erro ${r.status}`); return r.json() })
      .then((d: RankingsAno) => { if (ativo) { setDados(d); setErro('') } })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [ano])

  const itensExibidos = cargo ? (dados.por_cargo[cargo] ?? []) : dados.geral

  return (
    <div>
      <h1>Rankings — quem mais gastou</h1>
      <div className="filtros">
        <select
          value={ano ?? ''}
          onChange={(e) => setAno(e.target.value ? Number(e.target.value) : undefined)}
        >
          {[...anos].sort((a, b) => b - a).map((a) => <option key={a} value={a}>{a}</option>)}
          <option value="">Todos os anos</option>
        </select>
        <select value={cargo} onChange={(e) => setCargo(e.target.value)}>
          <option value="">Todos os cargos</option>
          <option value="Deputado Federal">Deputados Federais</option>
          <option value="Senador">Senadores</option>
          <option value="Deputado Distrital">Deputados Distritais</option>
        </select>
      </div>
      {erro && <p className="cartao">⚠️ {erro}</p>}
      <div className="cartao">
        {itensExibidos.length === 0 ? (
          <p>Nenhum parlamentar deste cargo no período.</p>
        ) : (
          <table>
            <thead>
              <tr><th>#</th><th>Político</th><th>Cargo</th><th>Partido/UF</th><th className="valor">Total</th></tr>
            </thead>
            <tbody>
              {itensExibidos.map((item, i) => (
                <tr key={item.politico.id}>
                  <td>{i + 1}º</td>
                  <td><Link href={`/politico/${item.politico.id}`}>{item.politico.nome}</Link></td>
                  <td>{item.politico.cargo}</td>
                  <td>{[item.politico.partido, item.politico.uf].filter(Boolean).join('/') || '—'}</td>
                  <td className="valor">{formatarBRL(item.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
