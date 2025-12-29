/**
 * Notification IPC Handlers
 *
 * Sets up IPC handlers for notification operations.
 * Connects the renderer process to the NotificationService in the main process.
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { NotificationService } from '../services/notification-service';

/**
 * Sets up IPC handlers for notification operations.
 */
export function setupNotificationHandlers(): void {
  const notificationService = NotificationService.getInstance();

  ipcMain.handle(IPC_CHANNELS.NOTIFICATION_SHOW, async (_, { type, title, message }) => {
    return notificationService.show(type, title, message);
  });

  ipcMain.handle(IPC_CHANNELS.NOTIFICATION_GET_HISTORY, async () => {
    return notificationService.getHistory();
  });

  ipcMain.handle(IPC_CHANNELS.NOTIFICATION_MARK_READ, async (_, id: string) => {
    notificationService.markRead(id);
    return { success: true };
  });

  ipcMain.handle(IPC_CHANNELS.NOTIFICATION_CLEAR_ALL, async () => {
    notificationService.clearAll();
    return { success: true };
  });

  console.warn('[IPC] Notification handlers registered');
}
