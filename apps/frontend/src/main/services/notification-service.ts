/**
 * Notification Service - Manages application notifications
 *
 * This service runs in the main process and handles both in-app and desktop notifications.
 * Supports budget alerts, anomaly warnings, and completion notifications.
 */

import { Notification as ElectronNotification } from 'electron';
import { v4 as uuidv4 } from 'uuid';
import type { Notification, NotificationPreferences } from '../../shared/types/notification';

// Maximum number of notifications to keep in history
const MAX_NOTIFICATIONS = 100;

/**
 * Service for managing application notifications.
 * Handles both in-app and desktop notifications.
 */
export class NotificationService {
  private static instance: NotificationService;
  private notifications: Notification[] = [];
  private preferences: NotificationPreferences = {
    enabled: true,
    soundEnabled: true,
    desktopEnabled: true,
    types: {
      budget: true,
      anomaly: true,
      completion: true
    }
  };

  /**
   * Get the singleton instance of the notification service
   */
  static getInstance(): NotificationService {
    if (!NotificationService.instance) {
      NotificationService.instance = new NotificationService();
    }
    return NotificationService.instance;
  }

  /**
   * Show a notification and optionally display a desktop notification.
   * @param type - The type of notification (info, warning, error, success)
   * @param title - The notification title
   * @param message - The notification message
   * @param action - Optional action configuration
   * @returns The created notification object
   */
  show(
    type: Notification['type'],
    title: string,
    message: string,
    action?: Notification['action']
  ): Notification {
    const notification: Notification = {
      id: uuidv4(),
      type,
      title,
      message,
      timestamp: new Date().toISOString(),
      read: false,
      action
    };

    // Add to the beginning of the array (most recent first)
    this.notifications.unshift(notification);

    // Keep only the last MAX_NOTIFICATIONS
    if (this.notifications.length > MAX_NOTIFICATIONS) {
      this.notifications = this.notifications.slice(0, MAX_NOTIFICATIONS);
    }

    // Show desktop notification if enabled
    if (this.preferences.enabled && this.preferences.desktopEnabled) {
      this.showDesktopNotification(title, message);
    }

    return notification;
  }

  /**
   * Show a desktop notification using Electron's Notification API
   */
  private showDesktopNotification(title: string, body: string): void {
    try {
      const desktopNotification = new ElectronNotification({
        title,
        body,
        silent: !this.preferences.soundEnabled
      });
      desktopNotification.show();
    } catch (error) {
      console.error('[notification-service] Failed to show desktop notification:', error);
    }
  }

  /**
   * Get the notification history
   * @returns Array of notifications sorted by timestamp (most recent first)
   */
  getHistory(): Notification[] {
    return [...this.notifications];
  }

  /**
   * Get the count of unread notifications
   */
  getUnreadCount(): number {
    return this.notifications.filter(n => !n.read).length;
  }

  /**
   * Mark a specific notification as read
   * @param id - The notification ID to mark as read
   */
  markRead(id: string): void {
    const notification = this.notifications.find(n => n.id === id);
    if (notification) {
      notification.read = true;
    }
  }

  /**
   * Mark all notifications as read
   */
  markAllRead(): void {
    this.notifications.forEach(n => {
      n.read = true;
    });
  }

  /**
   * Clear all notifications
   */
  clearAll(): void {
    this.notifications = [];
  }

  /**
   * Get current notification preferences
   */
  getPreferences(): NotificationPreferences {
    return { ...this.preferences };
  }

  /**
   * Update notification preferences
   * @param preferences - Partial preferences to update
   */
  setPreferences(preferences: Partial<NotificationPreferences>): void {
    this.preferences = {
      ...this.preferences,
      ...preferences,
      types: {
        ...this.preferences.types,
        ...(preferences.types || {})
      }
    };
  }

  /**
   * Show a budget alert notification
   * @param percentage - The current budget usage percentage
   * @param threshold - The threshold that was exceeded
   */
  showBudgetAlert(percentage: number, threshold: number): Notification {
    const type = percentage >= 100 ? 'error' : 'warning';
    const title = percentage >= 100 ? 'Budget Exceeded' : 'Budget Warning';
    const message = `You have used ${percentage.toFixed(1)}% of your budget (threshold: ${threshold}%)`;

    return this.show(type, title, message, {
      label: 'View Settings',
      handler: 'openSettings'
    });
  }

  /**
   * Show an anomaly detection notification
   * @param anomalyType - The type of anomaly detected
   * @param details - Additional details about the anomaly
   */
  showAnomalyWarning(anomalyType: string, details: string): Notification {
    return this.show('warning', `Anomaly Detected: ${anomalyType}`, details, {
      label: 'View Details',
      handler: 'navigate'
    });
  }

  /**
   * Show a task completion notification
   * @param specId - The spec ID that completed
   * @param specName - The name of the completed spec
   * @param success - Whether the task completed successfully
   */
  showCompletionNotification(specId: string, specName: string, success: boolean): Notification {
    const type = success ? 'success' : 'error';
    const title = success ? 'Task Completed' : 'Task Failed';
    const message = success
      ? `"${specName}" has completed successfully`
      : `"${specName}" failed to complete`;

    return this.show(type, title, message, {
      label: 'View Spec',
      handler: 'viewSpec'
    });
  }
}

// Export singleton instance getter for convenience
export function getNotificationService(): NotificationService {
  return NotificationService.getInstance();
}
