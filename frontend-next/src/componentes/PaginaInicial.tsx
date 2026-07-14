'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { filtrarPoliticos } from '@/lib/busca'
import type { Politico, VisaoGeral } from '@/lib/tipos'
import { Panorama } from './Panorama'

export function PaginaInicial({ inicial, anos }: { inicial: VisaoGeral; anos: number[] }) {
  const [indice, setIndice] = useState<Politico[] | null>(null)
  const [busca, setBusca] = useState('')
  const [erro, setErro] = useState('')

  useEffect(() => {
    let ativo = true
    fetch('/dados/politicos.json')
      .then((r) => { if (!r.ok) throw new Error(`Erro ${r.status} ao carregar o índice`); return r.json() })
      .then((lista) => { if (ativo) setIndice(lista) })
      .catch((e) => { if (ativo) setErro(e.message) })
    return () => { ativo = false }
  }, [])

  const ativa = busca.trim().length >= 3
  const resultados = ativa && indice ? filtrarPoliticos(indice, busca) : []

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
      {ativa && !indice && !erro && <p>Carregando índice...</p>}
      {resultados.map((p) => (
        <Link key={p.id} href={`/politico/${p.id}`}>
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
      {ativa && indice && resultados.length === 0 && <p>Nenhum político encontrado.</p>}
      {!ativa && <Panorama inicial={inicial} anos={anos} />}
    </div>
  )
}
