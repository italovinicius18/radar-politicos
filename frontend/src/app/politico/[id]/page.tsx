import type { Metadata } from 'next'
import { Perfil } from '@/componentes/Perfil'
import { lerPerfil, lerPoliticos } from '@/lib/dados-build'
import { formatarBRLCompacto } from '@/lib/formato'

export function generateStaticParams() {
  return lerPoliticos().map((p) => ({ id: p.id }))
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params
  const resumo = lerPerfil(decodeURIComponent(id))
  const p = resumo.politico
  const filiacao = [p.partido, p.uf].filter(Boolean).join('/')
  const anos = resumo.por_ano.map((a) => a.ano)
  const periodo = anos.length ? `${Math.min(...anos)}–${Math.max(...anos)}` : ''
  return {
    title: `Gastos de ${p.nome}${filiacao ? ` (${filiacao})` : ''} — Radar Políticos`,
    description: `${p.cargo} ${p.nome}: ${formatarBRLCompacto(resumo.total)} em verbas públicas (${periodo}). Veja categorias, fornecedores e notas fiscais.`,
    openGraph: { images: [p.foto_url ?? '/og-padrao.png'] },
  }
}

export default async function Pagina({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const resumo = lerPerfil(decodeURIComponent(id))
  return <Perfil resumo={resumo} />
}
