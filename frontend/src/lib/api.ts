export interface Politico {
  id: string
  nome: string
  cargo: string
  partido: string | null
  uf: string | null
  foto_url: string | null
  fonte: string
}

export interface Resumo {
  politico: Politico
  total: number
  por_ano: { ano: number; total: number }[]
  por_categoria: { categoria: string; total: number }[]
  top_fornecedores: { fornecedor: string; cnpj: string; total: number; quantidade: number }[]
}

export interface Despesa {
  ano: number
  mes: number | null
  data: string | null
  categoria: string
  categoria_original: string
  descricao: string | null
  fornecedor: string | null
  fornecedor_cnpj: string | null
  valor: number
  documento_url: string | null
  fonte: string
}

export interface PaginaDespesas {
  total_itens: number
  pagina: number
  por_pagina: number
  itens: Despesa[]
}

export interface ItemRanking {
  politico: Politico
  total: number
}

async function obter<T>(caminho: string, parametros: Record<string, string | number | undefined>): Promise<T> {
  const query = new URLSearchParams()
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== '') query.set(chave, String(valor))
  }
  const resposta = await fetch(`${caminho}?${query}`)
  if (!resposta.ok) throw new Error(`Erro ${resposta.status} ao consultar a API`)
  return resposta.json()
}

export const buscarPoliticos = (busca: string) =>
  obter<Politico[]>('/api/politicos', { busca })

export const obterResumo = (id: string, anoInicio?: number, anoFim?: number) =>
  obter<Resumo>(`/api/politicos/${id}/resumo`, { ano_inicio: anoInicio, ano_fim: anoFim })

export const obterDespesas = (
  id: string,
  filtros: { ano?: number; categoria?: string; ordenar?: string; pagina?: number },
) => obter<PaginaDespesas>(`/api/politicos/${id}/despesas`, filtros)

export const obterRankings = (filtros: { ano?: number; cargo?: string; categoria?: string }) =>
  obter<ItemRanking[]>('/api/rankings', filtros)
