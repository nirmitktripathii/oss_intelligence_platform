import { MetadataRoute } from 'next';
import { SAMPLE_FALLBACK_ISSUES } from '@/lib/constants';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://gitscout.dev';

  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: `${baseUrl}`,
      lastModified: new Date(),
      changeFrequency: 'always',
      priority: 1.0,
    },
    {
      url: `${baseUrl}/graph`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.7,
    },
  ];

  const dynamicIssueRoutes: MetadataRoute.Sitemap = SAMPLE_FALLBACK_ISSUES.map((issue) => ({
    url: `${baseUrl}/issues/${encodeURIComponent(issue.id)}`,
    lastModified: new Date(issue.updatedAt || issue.createdAt),
    changeFrequency: 'daily',
    priority: 0.9,
  }));

  return [...staticRoutes, ...dynamicIssueRoutes];
}
