import { Domain, Difficulty } from './issue';

export type ChannelType = 'telegram' | 'discord' | 'email' | 'whatsapp';

export interface NotificationSubscription {
  id: string;
  channel: ChannelType;
  destination: string; // chat_id, webhook_url, email address, phone
  domains: (Domain | string)[];
  minBountyUsd: number;
  difficulties?: (Difficulty | string)[];
  techStack?: string[];
  digestFrequency?: 'instant' | 'daily' | 'weekly';
  isActive: boolean;
  createdAt: string;
  lastNotifiedAt?: string;
}

export interface SubscriptionCreate {
  channel: ChannelType;
  destination: string;
  domains: string[];
  minBountyUsd: number;
  difficulties?: string[];
  techStack?: string[];
  digestFrequency?: 'instant' | 'daily' | 'weekly';
}

export interface TestNotificationRequest {
  channel: ChannelType;
  destination: string;
  issueId?: string;
}

export interface TestNotificationResponse {
  success: boolean;
  message: string;
  channel: ChannelType;
  timestamp: string;
}
