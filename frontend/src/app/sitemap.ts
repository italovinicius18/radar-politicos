import type { MetadataRoute } from 'next'
import { lerPoliticos } from '@/lib/dados-build'
import { URL_BASE as BASE } from '@/lib/site'

export const dynamic = 'force-static'

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
