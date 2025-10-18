interface Notification {
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message: string;
  duration?: number;
}

type NotificationFn = (notification: Omit<Notification, 'id'>) => string;

interface ApiClientOptions extends RequestInit {
  onError?: (type: 'success' | 'error' | 'info' | 'warning', title: string, message: string) => void;
  suppressErrorNotification?: boolean;
}

class ApiClient {
  private notifyFn?: NotificationFn;

  setNotificationHandler(fn: NotificationFn) {
    this.notifyFn = fn;
  }

  async request<T = any>(
    url: string,
    options: RequestInit & ApiClientOptions = {}
  ): Promise<T> {
    const { onError, suppressErrorNotification, ...fetchOptions } = options;

    try {
      const response = await fetch(url, fetchOptions);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData?.detail || errorData?.message || `Request failed with status ${response.status}`;
        throw new Error(message);
      }

      return await response.json();
    } catch (error: any) {
      const errorMessage = error?.message || 'Network request failed';
      
      // Notify via callback or global handler
      if (!suppressErrorNotification) {
        if (onError) {
          onError('error', 'Request Failed', errorMessage);
        } else if (this.notifyFn) {
          this.notifyFn({
            type: 'error',
            title: 'Request Failed',
            message: errorMessage
          });
        }
      }

      throw error;
    }
  }

  async get<T = any>(url: string, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'GET' });
  }

  async post<T = any>(url: string, body: any, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      body: JSON.stringify(body)
    });
  }

  async put<T = any>(url: string, body: any, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      body: JSON.stringify(body)
    });
  }

  async delete<T = any>(url: string, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
