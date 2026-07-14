import { PaginaInicial } from '@/componentes/PaginaInicial'
import { lerMeta, lerVisaoGeral } from '@/lib/dados-build'

export default function Home() {
  const meta = lerMeta()
  const inicial = lerVisaoGeral(meta.ano_max!)
  return <PaginaInicial inicial={inicial} anos={meta.anos} />
}
