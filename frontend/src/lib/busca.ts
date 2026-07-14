import type { Politico } from './tipos'

export function semAcento(texto: string): string {
  return texto.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

export function filtrarPoliticos(lista: Politico[], termo: string, limite = 20): Politico[] {
  const chave = semAcento(termo)
  if (chave.length < 3) return []
  return lista.filter((p) => semAcento(p.nome).includes(chave)).slice(0, limite)
}
