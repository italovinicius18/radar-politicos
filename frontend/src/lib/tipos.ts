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

export interface NotaMaisCara {
  valor: number
  categoria: string
  fornecedor: string | null
  data: string | null
  politico: Politico
}

export interface VisaoGeral {
  ano: number
  kpis: {
    total: number
    total_mesmo_periodo_anterior: number
    variacao_pct: number | null
    meses_com_dados: number
    parlamentares: number
    por_cargo: { cargo: string; quantidade: number }[]
    media_por_parlamentar: number
    num_despesas: number
    nota_mais_cara: NotaMaisCara | null
  }
  por_mes: { mes: number; total: number }[]
  por_casa: { fonte: string; rotulo: string; total: number; parlamentares: number; media: number; mediana: number }[]
  top_gastadores: ItemRanking[]
  top_categorias: { categoria: string; total: number }[]
  top_fornecedores: { fornecedor: string; cnpj: string; total: number; quantidade: number }[]
  por_partido: { partido: string; parlamentares: number; media: number; mediana: number }[]
  media_por_uf: { uf: string; parlamentares: number; media: number }[]
  estatisticas: {
    fim_de_ano: { ano_ref: number; dezembro: number; media_mensal: number; variacao_pct: number } | null
    transparencia: { pct_com_documento: number; por_fonte: { fonte: string; rotulo: string; pct: number }[] } | null
    concentracao_top10_pct: number | null
    quase_exclusivos: {
      quantidade: number
      maior: {
        fornecedor: string
        cnpj: string
        total: number
        pct_um_parlamentar: number
        politico: { id: string; nome: string }
      } | null
    }
  }
}

export interface Meta {
  gerado_em: string
  anos: number[]
  ano_max: number | null
  total_politicos: number
  total_despesas: number
}

export interface RankingsAno {
  geral: ItemRanking[]
  por_cargo: Record<string, ItemRanking[]>
}

export interface DespesasCompactas {
  colunas: string[]
  linhas: (string | number | null)[][]
}
