// apps/frontend/src/shared/types/notification.ts

/**
 * Notification System Types
 * Types for user notifications including budget alerts, anomaly warnings, and completion events
 */

export interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  action?: {
    label: string;
    handler: string;
  };
}

export interface NotificationPreferences {
  enabled: boolean;
  soundEnabled: boolean;
  desktopEnabled: boolean;
  types: {
    budget: boolean;
    anomaly: boolean;
    completion: boolean;
  };
}
