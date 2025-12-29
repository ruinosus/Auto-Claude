import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Bell, Check, Trash2, AlertTriangle, Info, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from './ui/popover';
import { ScrollArea } from './ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { useNotificationStore } from '../stores/notification-store';
import { cn } from '../lib/utils';
import type { Notification } from '../../shared/types/notification';

const typeIcons: Record<Notification['type'], typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  error: AlertCircle,
  success: CheckCircle,
};

const typeColors: Record<Notification['type'], string> = {
  info: 'text-blue-500',
  warning: 'text-yellow-500',
  error: 'text-red-500',
  success: 'text-green-500',
};

export function NotificationCenter() {
  const { t } = useTranslation(['analytics']);
  const {
    notifications,
    unreadCount,
    fetchNotifications,
    markRead,
    markAllRead,
    clearAll,
  } = useNotificationStore();

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  return (
    <Popover>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              aria-label={t('analytics:notifications.title')}
              aria-haspopup="dialog"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <Badge
                  variant="destructive"
                  className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
                  aria-label={`${unreadCount} ${t('analytics:notifications.title').toLowerCase()}`}
                >
                  {unreadCount > 9 ? '9+' : unreadCount}
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {t('analytics:notifications.title')}
        </TooltipContent>
      </Tooltip>
      <PopoverContent
        className="w-80 p-0"
        align="end"
        role="dialog"
        aria-label={t('analytics:notifications.title')}
      >
        <div className="flex items-center justify-between p-3 border-b">
          <h4 className="font-semibold" id="notification-center-title">
            {t('analytics:notifications.title')}
          </h4>
          <div className="flex gap-1">
            {unreadCount > 0 && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={markAllRead}
                    aria-label={t('analytics:notifications.markAllRead')}
                  >
                    <Check className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {t('analytics:notifications.markAllRead')}
                </TooltipContent>
              </Tooltip>
            )}
            {notifications.length > 0 && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearAll}
                    aria-label={t('analytics:notifications.clearAll')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {t('analytics:notifications.clearAll')}
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>

        <ScrollArea className="h-[300px]">
          {notifications.length === 0 ? (
            <div
              className="p-4 text-center text-muted-foreground"
              role="status"
              aria-live="polite"
            >
              {t('analytics:notifications.noNotifications')}
            </div>
          ) : (
            <div className="divide-y" role="list" aria-label={t('analytics:notifications.title')}>
              {notifications.map(notification => {
                const Icon = typeIcons[notification.type];
                return (
                  <div
                    key={notification.id}
                    className={cn(
                      'p-3 cursor-pointer hover:bg-muted/50 transition-colors',
                      !notification.read && 'bg-muted/30'
                    )}
                    onClick={() => !notification.read && markRead(notification.id)}
                    onKeyDown={(e) => {
                      if ((e.key === 'Enter' || e.key === ' ') && !notification.read) {
                        e.preventDefault();
                        markRead(notification.id);
                      }
                    }}
                    role="listitem"
                    tabIndex={0}
                    aria-label={`${notification.title}: ${notification.message}${!notification.read ? ' (unread)' : ''}`}
                  >
                    <div className="flex gap-2">
                      <Icon
                        className={cn('h-5 w-5 flex-shrink-0', typeColors[notification.type])}
                        aria-hidden="true"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm">{notification.title}</p>
                        <p className="text-sm text-muted-foreground truncate">
                          {notification.message}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          <time dateTime={notification.timestamp}>
                            {new Date(notification.timestamp).toLocaleString()}
                          </time>
                        </p>
                      </div>
                      {!notification.read && (
                        <span
                          className="h-2 w-2 rounded-full bg-primary flex-shrink-0 mt-1.5"
                          aria-hidden="true"
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
