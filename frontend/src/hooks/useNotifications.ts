import { useState, useEffect } from 'react';
import notificationService from '../services/notificationService';

export const useNotifications = () => {
  const [notifications, setNotifications] = useState(notificationService.getNotifications());
  const [unreadCount, setUnreadCount] = useState(notificationService.getUnreadCount());

  useEffect(() => {
    const unsubscribe = notificationService.subscribe((updatedNotifications) => {
      setNotifications(updatedNotifications);
      setUnreadCount(notificationService.getUnreadCount());
    });

    // Initialize with current notifications
    setNotifications(notificationService.getNotifications());
    setUnreadCount(notificationService.getUnreadCount());

    return () => unsubscribe();
  }, []);

  const markAsRead = (id: string) => {
    notificationService.markAsRead(id);
  };

  const markAllAsRead = () => {
    notificationService.markAllAsRead();
  };

  const removeNotification = (id: string) => {
    notificationService.removeNotification(id);
  };

  const addNotification = (notification: Omit<import('../services/notificationService').NotificationMessage, 'id' | 'timestamp' | 'read'>) => {
    notificationService.addNotification(notification);
  };

  return {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    removeNotification,
    addNotification
  };
};
