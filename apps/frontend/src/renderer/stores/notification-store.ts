/**
 * Notification Store - Zustand store for managing notifications in the renderer
 *
 * This store manages notification state and provides actions for interacting
 * with the notification service in the main process via IPC.
 */

import { create } from 'zustand';
import type { Notification } from '../../shared/types/notification';
import { IPC_CHANNELS } from '../../shared/constants/ipc';

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;

  // Actions
  setNotifications: (notifications: Notification[]) => void;
  addNotification: (notification: Notification) => void;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  clearAll: () => Promise<void>;
  fetchNotifications: () => Promise<void>;
}

const initialState = {
  notifications: [],
  unreadCount: 0,
  isLoading: false,
};

export const useNotificationStore = create<NotificationState>((set, get) => ({
  ...initialState,

  setNotifications: (notifications) => {
    set({
      notifications,
      unreadCount: notifications.filter(n => !n.read).length
    });
  },

  addNotification: (notification) => {
    set(state => ({
      notifications: [notification, ...state.notifications],
      unreadCount: notification.read ? state.unreadCount : state.unreadCount + 1
    }));
  },

  markRead: async (id) => {
    try {
      await window.electron.ipcRenderer.invoke(IPC_CHANNELS.NOTIFICATION_MARK_READ, id);
      set(state => {
        const notification = state.notifications.find(n => n.id === id);
        const wasUnread = notification && !notification.read;
        return {
          notifications: state.notifications.map(n =>
            n.id === id ? { ...n, read: true } : n
          ),
          unreadCount: wasUnread ? Math.max(0, state.unreadCount - 1) : state.unreadCount
        };
      });
    } catch (error) {
      console.error('[notification-store] Failed to mark notification as read:', error);
    }
  },

  markAllRead: async () => {
    try {
      // Note: Would call IPC in full implementation when backend handler is registered
      set(state => ({
        notifications: state.notifications.map(n => ({ ...n, read: true })),
        unreadCount: 0
      }));
    } catch (error) {
      console.error('[notification-store] Failed to mark all notifications as read:', error);
    }
  },

  clearAll: async () => {
    try {
      await window.electron.ipcRenderer.invoke(IPC_CHANNELS.NOTIFICATION_CLEAR_ALL);
      set({ notifications: [], unreadCount: 0 });
    } catch (error) {
      console.error('[notification-store] Failed to clear notifications:', error);
    }
  },

  fetchNotifications: async () => {
    set({ isLoading: true });
    try {
      const notifications = await window.electron.ipcRenderer.invoke(
        IPC_CHANNELS.NOTIFICATION_GET_HISTORY
      );
      get().setNotifications(notifications || []);
    } catch (error) {
      console.error('[notification-store] Failed to fetch notifications:', error);
    } finally {
      set({ isLoading: false });
    }
  }
}));

// Helper functions for external use

export function setNotifications(notifications: Notification[]): void {
  useNotificationStore.getState().setNotifications(notifications);
}

export function addNotification(notification: Notification): void {
  useNotificationStore.getState().addNotification(notification);
}

export async function markNotificationRead(id: string): Promise<void> {
  return useNotificationStore.getState().markRead(id);
}

export async function markAllNotificationsRead(): Promise<void> {
  return useNotificationStore.getState().markAllRead();
}

export async function clearAllNotifications(): Promise<void> {
  return useNotificationStore.getState().clearAll();
}

export async function fetchNotifications(): Promise<void> {
  return useNotificationStore.getState().fetchNotifications();
}

// Get current state snapshots

export function getNotifications(): Notification[] {
  return useNotificationStore.getState().notifications;
}

export function getUnreadCount(): number {
  return useNotificationStore.getState().unreadCount;
}

export function isNotificationsLoading(): boolean {
  return useNotificationStore.getState().isLoading;
}
