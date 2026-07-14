import type { Metadata } from 'next'
import { Rankings } from '@/componentes/Rankings'
import { lerMeta, lerRankings } from '@/lib/dados-build'

export const metadata: Metadata = {
  title: 'Rankings — quem mais gastou — Radar Políticos',
  description:
    'Ranking de deputados federais, senadores e deputados distritais por total de verbas públicas gastas, por ano.',
}

export default function Pagina() {
  const meta = lerMeta()
  const anoInicial = meta.ano_max ?? Math.max(...meta.anos)
  const itensIniciais = lerRankings(anoInicial)
  return <Rankings anos={meta.anos} anoInicial={anoInicial} itensIniciais={itensIniciais} />
}
