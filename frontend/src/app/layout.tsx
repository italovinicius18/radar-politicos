import type { Metadata } from 'next'
import Link from 'next/link'
import '@fontsource-variable/archivo/index.css'
import '@fontsource/ibm-plex-mono/500.css'
import '@fontsource/ibm-plex-mono/600.css'
import './globals.css'
import { lerMeta } from '@/lib/dados-build'
import { formatarData } from '@/lib/formato'
import { URL_BASE } from '@/lib/site'

export const metadata: Metadata = {
  metadataBase: new URL(URL_BASE),
  title: 'Radar Políticos — gastos parlamentares abertos',
  description:
    'Gastos de deputados federais, senadores e deputados distritais (2013–2026), direto das bases abertas oficiais: o quê, com quem, quanto e a nota fiscal.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = lerMeta()
  return (
    <html lang="pt-BR">
      <body>
        <header className="cabecalho">
          <div className="container">
            <Link href="/" className="wordmark"><span>⦿</span>Radar Políticos</Link>
            <nav>
              <Link href="/rankings">Rankings</Link>
            </nav>
            <span className="status-base">
              base: <b>3 casas</b> · {meta.total_despesas.toLocaleString('pt-BR')} despesas ·{' '}
              <b>{meta.anos[0]}–{meta.ano_max}</b>
            </span>
          </div>
        </header>
        <main className="container">{children}</main>
        <footer className="rodape">
          <div className="container">
            <strong>O Radar Políticos não tem vínculo nem viés político-partidário.</strong>{' '}
            Todos os dados vêm das bases abertas oficiais — Câmara dos Deputados (CEAP), Senado
            Federal (CEAPS) e Câmara Legislativa do DF — e são apresentados como publicados, sem
            edição. O objetivo é dar ao cidadão acesso claro à informação que já é pública. Dados
            atualizados em {formatarData(meta.gerado_em.slice(0, 10))}.
          </div>
        </footer>
      </body>
    </html>
  )
}
