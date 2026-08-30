import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://gitscout.dev';

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/'],
      },
      {
        userAgent: ['GPTBot', 'ChatGPT-User', 'PerplexityBot', 'ClaudeBot', 'AnthropicAI'],
        allow: ['/', '/issues/*', '/graph', '/pricing', '/llms.txt'],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
