import { describe, expect, it } from 'vitest'
import { filtrarPoliticos, semAcento } from './busca'

const LISTA = [
  { id: 'a', nome: 'José Ávila', cargo: 'Deputado Federal', partido: 'PT', uf: 'SP', foto_url: null, fonte: 'camara' },
  { id: 'b', nome: 'JOÃO NETO', cargo: 'Senador', partido: null, uf: null, foto_url: null, fonte: 'senado' },
]

describe('semAcento', () => {
  it('remove acentos e baixa caixa', () => {
    expect(semAcento('José ÁVILA')).toBe('jose avila')
  })
})

describe('filtrarPoliticos', () => {
  it('acha por trecho sem acento', () => {
    expect(filtrarPoliticos(LISTA, 'jose av').map((p) => p.id)).toEqual(['a'])
    expect(filtrarPoliticos(LISTA, 'joao').map((p) => p.id)).toEqual(['b'])
  })
  it('vazio com menos de 3 letras', () => {
    expect(filtrarPoliticos(LISTA, 'jo')).toEqual([])
  })
})
