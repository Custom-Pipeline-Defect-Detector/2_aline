// Notification Service for handling document processing notifications
class NotificationService {
  private static instance: NotificationService;
  private listeners: Array<(notifications: NotificationMessage[]) => void> = [];
  private notifications: NotificationMessage[] = [];
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  public static getInstance(): NotificationService {
    if (!NotificationService.instance) {
      NotificationService.instance = new NotificationService();
    }
    return NotificationService.instance;
  }

  public subscribe(listener: (notifications: NotificationMessage[]) => void): () => void {
    this.listeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  public notify(notification: NotificationMessage): void {
    // Add the new notification to the list
    this.notifications = [notification, ...this.notifications];
    this.listeners.forEach(listener => listener(this.notifications));
  }

  public getNotifications(): NotificationMessage[] {
    return this.notifications;
  }

  public getUnreadCount(): number {
    return this.notifications.filter(n => !n.read).length;
  }

  public connectWebSocket(userId: string): void {
    // In a real implementation, we would connect to a WebSocket server
    // For now, we'll simulate notifications
    
    // Simulate receiving notifications
    setTimeout(() => {
      this.notify({
        id: Date.now().toString(),
        type: 'info',
        title: 'Document Processing Started',
        message: 'Your document is being processed by AI agents',
        timestamp: new Date().toISOString(),
        read: false
      });
    }, 3000);

    setTimeout(() => {
      this.notify({
        id: (Date.now() + 1).toString(),
        type: 'success',
        title: 'Document Processing Complete',
        message: 'Your document has been successfully processed',
        timestamp: new Date().toISOString(),
        read: false
      });
    }, 8000);
  }

  public disconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  public markAsRead(notificationId: string): void {
    const index = this.notifications.findIndex(n => n.id === notificationId);
    if (index !== -1) {
      this.notifications[index].read = true;
      this.listeners.forEach(listener => listener(this.notifications));
    }
  }

  public markAllAsRead(): void {
    this.notifications = this.notifications.map(n => ({ ...n, read: true }));
    this.listeners.forEach(listener => listener(this.notifications));
  }

  public removeNotification(notificationId: string): void {
    this.notifications = this.notifications.filter(n => n.id !== notificationId);
    this.listeners.forEach(listener => listener(this.notifications));
  }

  public addNotification(notification: Omit<NotificationMessage, 'id' | 'timestamp' | 'read'>): void {
    const newNotification: NotificationMessage = {
      ...notification,
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      read: false
    };
    
    this.notify(newNotification);
  }
}

export interface NotificationMessage {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export default NotificationService.getInstance();
