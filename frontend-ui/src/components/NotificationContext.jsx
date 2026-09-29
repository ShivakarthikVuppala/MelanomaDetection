import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from './AuthContext';

const NotificationContext = createContext(null);

export function useNotification() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotification must be used within NotificationProvider');
  return ctx;
}

export function NotificationProvider({ children }) {
  const { user, token } = useAuth();
  const userId = user?.id || user?._id || user?.email || null;

  const storageKey = userId ? `meladetect_notification_${userId}` : null;

  const [notification, setNotification] = useState(() => {
    if (!storageKey) return { status: 'none', title: 'No New Notifications', message: 'There are no new notifications.', unread: false };
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) return JSON.parse(saved);
    } catch {
      // fallback
    }
    return { status: 'none', title: 'No New Notifications', message: 'There are no new notifications.', unread: false };
  });

  // When user changes or logs in/out, sync notification state
  useEffect(() => {
    if (!userId || !token) {
      setNotification({
        status: 'none',
        title: 'No New Notifications',
        message: 'There are no new notifications.',
        unread: false,
      });
      return;
    }

    let isMounted = true;
    const userStorageKey = `meladetect_notification_${userId}`;

    try {
      const saved = localStorage.getItem(userStorageKey);
      if (saved) {
        setNotification(JSON.parse(saved));
        return;
      }
    } catch {
      // ignore
    }

    // If no notification in localStorage, check user's latest analysis from server
    fetch('/api/analyses', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((list) => {
        if (!isMounted) return;
        if (Array.isArray(list) && list.length > 0) {
          const latest = list[0];
          const initialNotif = {
            status: 'completed',
            reportId: latest.analysis_id,
            reportData: latest,
            title: 'Report Generated',
            message: 'Your analysis report is ready to view.',
            unread: false,
            timestamp: latest.timestamp || new Date().toISOString(),
          };
          setNotification(initialNotif);
          try {
            localStorage.setItem(userStorageKey, JSON.stringify(initialNotif));
          } catch {
            // ignore
          }
        } else {
          setNotification({
            status: 'none',
            title: 'No New Notifications',
            message: 'There are no new notifications.',
            unread: false,
          });
        }
      })
      .catch(() => {
        if (isMounted) {
          setNotification({
            status: 'none',
            title: 'No New Notifications',
            message: 'There are no new notifications.',
            unread: false,
          });
        }
      });

    return () => {
      isMounted = false;
    };
  }, [userId, token]);

  // Persist notification whenever it changes for the active user
  useEffect(() => {
    if (!storageKey) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(notification));
    } catch {
      // ignore
    }
  }, [notification, storageKey]);

  const startReportRunning = useCallback(() => {
    setNotification({
      status: 'running',
      title: 'Report Running',
      message: 'Your analysis report is currently being generated.',
      unread: true,
      timestamp: new Date().toISOString(),
    });
  }, []);

  const setReportCompleted = useCallback((report) => {
    setNotification({
      status: 'completed',
      reportId: report?.analysis_id,
      reportData: report,
      title: 'Report Generated',
      message: 'Your analysis report is ready to view.',
      unread: true,
      timestamp: new Date().toISOString(),
    });
  }, []);

  const setReportFailed = useCallback((errorMsg) => {
    setNotification({
      status: 'failed',
      title: 'Report Generation Failed',
      message: errorMsg || 'Something went wrong while generating your report.',
      unread: true,
      timestamp: new Date().toISOString(),
    });
  }, []);

  const clearNotification = useCallback(() => {
    setNotification({
      status: 'none',
      title: 'No New Notifications',
      message: 'There are no new notifications.',
      unread: false,
    });
  }, []);

  const markAsRead = useCallback(() => {
    setNotification((prev) => ({ ...prev, unread: false }));
  }, []);

  const value = useMemo(
    () => ({
      notification,
      startReportRunning,
      setReportCompleted,
      setReportFailed,
      clearNotification,
      markAsRead,
    }),
    [notification, startReportRunning, setReportCompleted, setReportFailed, clearNotification, markAsRead],
  );

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}
