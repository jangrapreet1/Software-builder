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
          bg: 'bg-emerald-500/10',
          border: 'border-emerald-500/20',
          icon: 'fa-check-circle text-emerald-400',
          text: 'text-emerald-100',
          title: 'text-emerald-50'
        };
      case 'error':
        return {
          bg: 'bg-red-500/10',
          border: 'border-red-500/20',
          icon: 'fa-exclamation-circle text-red-400',
          text: 'text-red-100',
          title: 'text-red-50'
        };
      case 'warning':
        return {
          bg: 'bg-amber-500/10',
          border: 'border-amber-500/20',
          icon: 'fa-exclamation-triangle text-amber-400',
          text: 'text-amber-100',
          title: 'text-amber-50'
        };
      case 'info':
      default:
        return {
          bg: 'bg-blue-500/10',
          border: 'border-blue-500/20',
          icon: 'fa-info-circle text-blue-400',
          text: 'text-blue-100',
          title: 'text-blue-50'
        };
    }
  };

  const styles = getStyles();

  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (!notification.duration) return;
    const start = Date.now();
    const duration = notification.duration;
    const tick = () => {
      const elapsed = Date.now() - start;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);
    };
    const id = setInterval(tick, 50);
    return () => clearInterval(id);
  }, [notification.duration]);

  const accentColor =
    notification.type === 'success' ? '#10b981' :
    notification.type === 'error'   ? '#ef4444' :
    notification.type === 'warning' ? '#f59e0b' :
    '#3b82f6';

  return (
    <div
      className={`relative overflow-hidden ${styles.bg} border ${styles.border} backdrop-blur-xl rounded-xl shadow-2xl transition-all duration-300 transform ${
        isVisible ? 'translate-x-0 opacity-100 scale-100' : 'translate-x-full opacity-0 scale-95'
      }`}
      style={{ borderLeft: `3px solid ${accentColor}` }}
    >
      <div className="flex items-start p-4">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${styles.bg} mr-3 shrink-0 mt-0.5`}>
          <i className={`fas ${styles.icon} text-sm`}></i>
        </div>
        <div className="flex-1 min-w-0">
          <h4 className={`font-semibold text-sm ${styles.title} mb-0.5`}>{notification.title}</h4>
          <p className={`text-xs ${styles.text} opacity-80 leading-relaxed`}>{notification.message}</p>
          {notification.action && (
            <button
              onClick={notification.action.onClick}
              className={`mt-2 text-xs font-semibold ${styles.text} hover:text-white underline underline-offset-2 decoration-white/30`}
            >
              {notification.action.label} →
            </button>
          )}
        </div>
        <button
          onClick={handleDismiss}
          className={`ml-2 mt-0.5 ${styles.text} hover:opacity-70 transition text-xs shrink-0`}
        >
          <i className="fas fa-times"></i>
        </button>
      </div>

      {/* Progress timer bar */}
      {notification.duration && (
        <div className="h-0.5 bg-white/5 w-full">
          <div
            className="h-full transition-none rounded-full"
            style={{ width: `${progress}%`, background: accentColor, opacity: 0.4 }}
          ></div>
        </div>
      )}
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
