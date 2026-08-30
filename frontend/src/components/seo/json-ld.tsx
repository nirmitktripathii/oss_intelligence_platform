import * as React from 'react';
import { Issue } from '@/types/issue';
import { SITE_CONFIG } from '@/lib/constants';

interface IssueJsonLdProps {
  issue: Issue;
}

export function IssueJsonLd({ issue }: IssueJsonLdProps) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    headline: issue.title,
    description: issue.body ? issue.body.slice(0, 200) : issue.title,
    url: `${SITE_CONFIG.url}/issues/${encodeURIComponent(issue.id)}`,
    datePublished: issue.createdAt,
    dateModified: issue.updatedAt,
    author: {
      '@type': 'Organization',
      name: 'GitScout OSS Intelligence',
      url: SITE_CONFIG.url,
    },
    publisher: {
      '@type': 'Organization',
      name: 'GitScout',
      logo: {
        '@type': 'ImageObject',
        url: `${SITE_CONFIG.url}/logo.svg`,
      },
    },
    about: {
      '@type': 'SoftwareSourceCode',
      codeRepository: issue.repository.repoUrl,
      programmingLanguage: issue.repository.language,
      name: issue.repository.name,
    },
    offers:
      issue.bounty && issue.bounty.isFunded
        ? {
            '@type': 'Offer',
            price: issue.bounty.amountUsd,
            priceCurrency: issue.bounty.currency || 'USD',
            url: issue.bounty.sourceUrl || issue.issueUrl,
            availability: 'https://schema.org/InStock',
          }
        : undefined,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

export function PlatformJsonLd() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'GitScout / OSS Terminal',
    operatingSystem: 'Any',
    applicationCategory: 'DeveloperApplication',
    description: SITE_CONFIG.description,
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
    },
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.9',
      ratingCount: '1280',
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
