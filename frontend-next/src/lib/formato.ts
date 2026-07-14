const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const compacto = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export function formatarBRL(valor: number): string {
  return brl.format(valor)
}

export function formatarBRLCompacto(valor: number): string {
  const abs = Math.abs(valor)
  if (abs >= 1_000_000) return `R$ ${compacto.format(valor / 1_000_000)} mi`
  if (abs >= 1_000) return `R$ ${compacto.format(valor / 1_000)} mil`
  return formatarBRL(valor)
}

export function formatarData(iso: string | null): string {
  if (!iso) return '—'
  const [ano, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${ano}`
}

export const MESES_ABREV = [
  'jan', 'fev', 'mar', 'abr', 'mai', 'jun',
  'jul', 'ago', 'set', 'out', 'nov', 'dez',
]
