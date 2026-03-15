import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getNotifications, markNotificationRead } from "@/api/client";
import type { Notification } from "@/api/client";
import { Bell, Check, Inbox } from "lucide-react";

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const { data: notifications, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: getNotifications,
  });

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const unreadCount = notifications?.filter((n) => !n.read).length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Notifications</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {unreadCount > 0
              ? `${unreadCount} unread notification${unreadCount !== 1 ? "s" : ""}`
              : "All caught up"}
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4 animate-pulse"
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-gray-800 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <div className="h-3.5 bg-gray-800 rounded w-1/3" />
                  <div className="h-3 bg-gray-800 rounded w-2/3" />
                  <div className="h-2.5 bg-gray-800 rounded w-1/4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : !notifications || notifications.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gray-800/50 flex items-center justify-center mb-5">
            <Inbox size={28} className="text-gray-600" />
          </div>
          <h3 className="text-lg font-medium text-gray-300 mb-2">
            No notifications
          </h3>
          <p className="text-sm text-gray-500 max-w-xs">
            You'll see notifications here when there are updates.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <NotificationItem
              key={n.id}
              notification={n}
              onMarkRead={(id) => markReadMutation.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function NotificationItem({
  notification,
  onMarkRead,
}: {
  notification: Notification;
  onMarkRead: (id: string) => void;
}) {
  const timeAgo = formatTimeAgo(notification.created_at);

  return (
    <div
      className={`bg-gray-900 border rounded-lg p-4 transition-colors ${
        notification.read
          ? "border-gray-800 opacity-60"
          : "border-indigo-500/30"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
            notification.read ? "bg-gray-800" : "bg-indigo-500/20"
          }`}
        >
          <Bell
            size={14}
            className={notification.read ? "text-gray-500" : "text-indigo-400"}
          />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-100">
            {notification.title}
          </h3>
          <p className="text-sm text-gray-400 mt-0.5">{notification.message}</p>
          <p className="text-xs text-gray-600 mt-1.5">{timeAgo}</p>
        </div>
        {!notification.read && (
          <button
            onClick={() => onMarkRead(notification.id)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-green-400 hover:bg-gray-800 transition-colors flex-shrink-0"
            title="Mark as read"
          >
            <Check size={14} />
          </button>
        )}
      </div>
    </div>
  );
}

function formatTimeAgo(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}
