// Cores validadas pelo verificador do dataviz (par a par sobre #f5f5f2)
export const FONTES: Record<string, { rotulo: string; cor: string }> = {
  camara: { rotulo: 'Câmara', cor: '#1d7a4d' },
  senado: { rotulo: 'Senado', cor: '#0369a1' },
  cldf: { rotulo: 'CLDF', cor: '#a07d10' },
}

export function infoFonte(fonte: string): { rotulo: string; cor: string } {
  return FONTES[fonte] ?? { rotulo: fonte, cor: '#475569' }
}
