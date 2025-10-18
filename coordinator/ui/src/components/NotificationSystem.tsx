import React, { useState, useEffect } from 'react';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  duration?: number;
}

interface NotificationSystemProps {
  notifications: Notification[];
  onDismiss: (id: string) => void;
}

export const NotificationSystem: React.FC<NotificationSystemProps> = ({
  notifications,
  onDismiss
}) => {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-3 max-w-md">
      {notifications.map((notification) => (
        <NotificationCard
          key={notification.id}
          notification={notification}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  );
};

const NotificationCard: React.FC<{
  notification: Notification;
  onDismiss: (id: string) => void;
}> = ({ notification, onDismiss }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Animate in
    setTimeout(() => setIsVisible(true), 10);

    // Auto-dismiss after duration
    if (notification.duration) {
      const timer = setTimeout(() => {
        handleDismiss();
      }, notification.duration);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    setTimeout(() => onDismiss(notification.id), 300);
  };

  const getStyles = () => {
    switch (notification.type) {
      case 'success':
        return {
          bg: 'bg-green-50',
          border: 'border-green-200',
          icon: 'fa-check-circle text-green-600',
          text: 'text-green-800',
          title: 'text-green-900'
        };
      case 'error':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          icon: 'fa-exclamation-circle text-red-600',
          text: 'text-red-800',
          title: 'text-red-900'
        };
      case 'warning':
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          icon: 'fa-exclamation-triangle text-yellow-600',
          text: 'text-yellow-800',
          title: 'text-yellow-900'
        };
      case 'info':
      default:
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          icon: 'fa-info-circle text-blue-600',
          text: 'text-blue-800',
          title: 'text-blue-900'
        };
    }
  };

  const styles = getStyles();

  return (
    <div
      className={`${styles.bg} border ${styles.border} rounded-lg shadow-lg p-4 transition-all duration-300 transform ${
        isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      }`}
    >
      <div className="flex items-start">
        <i className={`fas ${styles.icon} mt-1 mr-3`}></i>
        <div className="flex-1">
          <h4 className={`font-semibold ${styles.title} mb-1`}>{notification.title}</h4>
          <p className={`text-sm ${styles.text}`}>{notification.message}</p>
          {notification.action && (
            <button
              onClick={notification.action.onClick}
              className={`mt-2 text-sm font-semibold ${styles.text} hover:underline`}
            >
              {notification.action.label} →
            </button>
          )}
        </div>
        <button
          onClick={handleDismiss}
          className={`ml-3 ${styles.text} hover:opacity-70 transition`}
        >
          <i className="fas fa-times"></i>
        </button>
      </div>
    </div>
  );
};

// Hook for managing notifications
export const useNotifications = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = (
    notification: Omit<Notification, 'id'>
  ): string => {
    const id = `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setNotifications((prev) => [...prev, { ...notification, id }]);
    return id;
  };

  const dismissNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const clearAll = () => {
    setNotifications([]);
  };

  return {
    notifications,
    addNotification,
    dismissNotification,
    clearAll
  };
};
