// apps/frontend/src/shared/types/notification.ts

/**
 * Notification System Types
 * Types for user notifications including budget alerts, anomaly warnings, and completion events
 */

/**
 * Represents a user notification with optional action handler
 */
export interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  action?: {
    label: string;
    handler: 'navigate' | 'dismiss' | 'openSettings' | 'viewSpec';
  };
}

/**
 * User preferences for notification delivery and filtering
 */
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
