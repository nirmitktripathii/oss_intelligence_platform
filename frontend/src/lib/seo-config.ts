import { Metadata } from 'next';
import { Issue } from '@/types/issue';
import { SITE_CONFIG } from './constants';

export const DEFAULT_METADATA: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'),
  title: {
    default: `${SITE_CONFIG.name} — ${SITE_CONFIG.tagline}`,
    template: `%s | ${SITE_CONFIG.name}`,
  },
  description: SITE_CONFIG.description,
  applicationName: SITE_CONFIG.name,
  authors: [{ name: SITE_CONFIG.author, url: SITE_CONFIG.url }],
  creator: SITE_CONFIG.author,
  publisher: SITE_CONFIG.name,
  keywords: [
    'Open Source',
    'GitHub Issues',
    'Bounties',
    'Polar.sh',
    'Algora',
    'AI Triage',
    'AST Localization',
    'Bug Reproduction',
    'Developer Tools',
    'Good First Issues',
    'PyTorch',
    'TypeScript',
    'Rust',
    'Next.js',
  ],
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: SITE_CONFIG.url,
    siteName: SITE_CONFIG.name,
    title: `${SITE_CONFIG.name} — Open-Source Intelligence & Contribution Terminal`,
    description: SITE_CONFIG.description,
    images: [
      {
        url: '/og-default.png',
        width: 1200,
        height: 630,
        alt: `${SITE_CONFIG.name} Terminal Interface`,
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: `${SITE_CONFIG.name} — Open-Source Intelligence & Contribution Terminal`,
    description: SITE_CONFIG.description,
    creator: '@gitscout_app',
    images: ['/og-default.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
};

export function generateIssueMetadata(issue: Issue): Metadata {
  const title = `[${issue.domain.toUpperCase()}] ${issue.title} — ${issue.repository.name} #${issue.githubIssueNumber}`;
  const bountyText = issue.bounty ? `💰 $${issue.bounty.amountUsd} Bounty | ` : '';
  const roiText = issue.hourlyRoiUsd ? `⚡ $${Math.round(issue.hourlyRoiUsd)}/hr ROI | ` : '';
  const description = `${bountyText}${roiText}AI-triaged fix blueprint, AST localized files, and minimal reproduction sandbox for ${issue.repository.owner}/${issue.repository.name} #${issue.githubIssueNumber}. Estimated solve time: ${issue.estimatedMinutesToSolve} mins.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: 'article',
      url: `/issues/${encodeURIComponent(issue.id)}`,
      publishedTime: issue.createdAt,
      modifiedTime: issue.updatedAt,
      tags: [...issue.techStack, issue.domain, issue.difficulty],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}
