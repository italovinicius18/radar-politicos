import type { MetadataRoute } from 'next'
import { lerPoliticos } from '@/lib/dados-build'

export const dynamic = 'force-static'
const BASE = 'https://radarpoliticos.com.br' // ajustar quando o domínio existir

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${BASE}/`, changeFrequency: 'daily', priority: 1 },
    { url: `${BASE}/rankings/`, changeFrequency: 'daily', priority: 0.8 },
    ...lerPoliticos().map((p) => ({
      url: `${BASE}/politico/${p.id}/`,
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    })),
  ]
}
