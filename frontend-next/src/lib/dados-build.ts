import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { Meta, Politico, Resumo, VisaoGeral } from './tipos'

const RAIZ = join(process.cwd(), 'public', 'dados')

function ler<T>(rel: string): T {
  return JSON.parse(readFileSync(join(RAIZ, rel), 'utf-8')) as T
}

export const lerMeta = () => ler<Meta>('meta.json')
export const lerPoliticos = () => ler<Politico[]>('politicos.json')
export const lerPerfil = (id: string) => ler<Resumo>(`perfil/${id}.json`)
export const lerVisaoGeral = (ano: number) => ler<VisaoGeral>(`visao-geral/${ano}.json`)
