/**
 * Notification API - Preload API for notification operations
 *
 * Provides methods for managing notifications via IPC to the main process.
 */

import { IPC_CHANNELS } from '../../../shared/constants';
import type { Notification } from '../../../shared/types/notification';
import { invokeIpc } from './ipc-utils';

/**
 * Notification API operations
 */
export interface NotificationAPI {
  // Operations
  getNotificationHistory: () => Promise<Notification[]>;
  markNotificationRead: (id: string) => Promise<void>;
  clearAllNotifications: () => Promise<void>;
}

/**
 * Creates the Notification API implementation
 */
export const createNotificationAPI = (): NotificationAPI => ({
  getNotificationHistory: (): Promise<Notification[]> =>
    invokeIpc(IPC_CHANNELS.NOTIFICATION_GET_HISTORY),

  markNotificationRead: (id: string): Promise<void> =>
    invokeIpc(IPC_CHANNELS.NOTIFICATION_MARK_READ, id),

  clearAllNotifications: (): Promise<void> =>
    invokeIpc(IPC_CHANNELS.NOTIFICATION_CLEAR_ALL)
});
