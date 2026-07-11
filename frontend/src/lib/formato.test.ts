import { describe, expect, it } from 'vitest'
import { formatarBRL, formatarData } from './formato'

describe('formatarBRL', () => {
  it('formata em pt-BR', () => {
    expect(formatarBRL(1234.5).replace(/\s/g, ' ')).toBe('R$ 1.234,50')
    expect(formatarBRL(-200).replace(/\s/g, ' ')).toBe('-R$ 200,00')
  })
})

describe('formatarData', () => {
  it('converte ISO para DD/MM/YYYY', () => {
    expect(formatarData('2025-02-07')).toBe('07/02/2025')
    expect(formatarData(null)).toBe('—')
  })
})
