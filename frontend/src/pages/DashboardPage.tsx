import { useQuery } from "@tanstack/react-query";
import {
  Users,
  BookOpen,
  BookCheck,
  HardDrive,
  Bell,
  CheckCircle,
  AlertCircle,
  Info,
  AlertTriangle,
  FolderOpen,
  Loader2,
} from "lucide-react";
import {
  getAuthors,
  getBooks,
  getNotifications,
  getRootFolders,
  getSystemStats,
  type Notification,
  type RootFolder,
} from "@/api/client";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + " " + units[i];
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const notificationIcon: Record<string, typeof Info> = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: AlertCircle,
};

const notificationColor: Record<string, string> = {
  info: "text-blue-400",
  success: "text-green-400",
  warning: "text-yellow-400",
  error: "text-red-400",
};

function StatCard({
  icon: Icon,
  label,
  value,
  loading,
}: {
  icon: typeof Users;
  label: string;
  value: string | number;
  loading: boolean;
}) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 flex items-center gap-4">
      <div className="p-2.5 rounded-lg bg-indigo-500/15">
        <Icon size={22} className="text-indigo-400" />
      </div>
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
        {loading ? (
          <div className="h-7 w-16 bg-gray-700 rounded animate-pulse mt-1" />
        ) : (
          <p className="text-2xl font-bold text-gray-100">{value}</p>
        )}
      </div>
    </div>
  );
}

function StorageBar({ folder }: { folder: RootFolder }) {
  const used = folder.total_space - folder.free_space;
  const pct = folder.total_space > 0 ? (used / folder.total_space) * 100 : 0;
  const barColor = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-yellow-500" : "bg-indigo-500";

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <FolderOpen size={16} className="text-gray-400" />
          <span className="text-sm font-medium text-gray-200">{folder.name || folder.path}</span>
          <span className="px-1.5 py-0.5 text-[10px] font-medium uppercase rounded bg-indigo-500/20 text-indigo-300">
            {folder.media_type}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          {folder.scan_status === "scanning" && (
            <span className="flex items-center gap-1 text-yellow-400">
              <Loader2 size={12} className="animate-spin" /> Scanning
            </span>
          )}
          {folder.scan_status === "idle" && folder.last_scan_at && (
            <span>Scanned {timeAgo(folder.last_scan_at)}</span>
          )}
        </div>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <div className="flex justify-between mt-1.5 text-xs text-gray-500">
        <span>{formatBytes(used)} used</span>
        <span>{formatBytes(folder.free_space)} free of {formatBytes(folder.total_space)}</span>
      </div>
    </div>
  );
}

function ActivityItem({ notification }: { notification: Notification }) {
  const Icon = notificationIcon[notification.notification_type] || Info;
  const color = notificationColor[notification.notification_type] || "text-gray-400";

  return (
    <div className="flex gap-3 py-3 border-b border-gray-800 last:border-0">
      <div className={`mt-0.5 ${color}`}>
        <Icon size={16} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200">{notification.title}</p>
        {notification.message && (
          <p className="text-xs text-gray-500 mt-0.5 truncate">{notification.message}</p>
        )}
      </div>
      <span className="text-xs text-gray-600 whitespace-nowrap">{timeAgo(notification.created_at)}</span>
    </div>
  );
}

export default function DashboardPage() {
  const { data: authors, isLoading: authorsLoading } = useQuery({
    queryKey: ["authors"],
    queryFn: () => getAuthors(),
  });

  const { data: booksData, isLoading: booksLoading } = useQuery({
    queryKey: ["books", "stats"],
    queryFn: () => getBooks({ page: 1, per_page: 1 }),
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["system-stats"],
    queryFn: getSystemStats,
  });

  const { data: rootFolders, isLoading: foldersLoading } = useQuery({
    queryKey: ["root-folders"],
    queryFn: getRootFolders,
  });

  const { data: notifications, isLoading: notifLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: getNotifications,
  });

  const totalAuthors = authors?.length ?? 0;
  const totalBooks = booksData?.total ?? 0;
  const booksOwned = stats?.library_items ?? 0;

  const totalStorage = rootFolders?.reduce((sum, f) => sum + f.total_space, 0) ?? 0;
  const freeStorage = rootFolders?.reduce((sum, f) => sum + f.free_space, 0) ?? 0;
  const usedStorage = totalStorage - freeStorage;

  const recentNotifications = notifications?.slice(0, 15) ?? [];

  return (
    <div className="space-y-8 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
        <p className="text-sm text-gray-400 mt-1">Library overview and recent activity</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Authors" value={totalAuthors} loading={authorsLoading} />
        <StatCard icon={BookOpen} label="Total Books" value={totalBooks} loading={booksLoading} />
        <StatCard icon={BookCheck} label="Books Owned" value={booksOwned} loading={statsLoading} />
        <StatCard
          icon={HardDrive}
          label="Storage Used"
          value={foldersLoading ? "" : formatBytes(usedStorage)}
          loading={foldersLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-4">
            <Bell size={18} className="text-indigo-400" />
            <h2 className="text-lg font-semibold text-gray-100">Recent Activity</h2>
          </div>
          {notifLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
              ))}
            </div>
          ) : recentNotifications.length === 0 ? (
            <p className="text-sm text-gray-500 py-8 text-center">No recent activity</p>
          ) : (
            <div className="divide-y divide-gray-800">
              {recentNotifications.map((n) => (
                <ActivityItem key={n.id} notification={n} />
              ))}
            </div>
          )}
        </div>

        {/* Root Folders / Storage */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-4">
            <HardDrive size={18} className="text-indigo-400" />
            <h2 className="text-lg font-semibold text-gray-100">Storage</h2>
          </div>
          {foldersLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-20 bg-gray-800 rounded animate-pulse" />
              ))}
            </div>
          ) : !rootFolders?.length ? (
            <p className="text-sm text-gray-500 py-8 text-center">No root folders configured</p>
          ) : (
            <div className="space-y-3">
              {rootFolders.map((folder) => (
                <StorageBar key={folder.id} folder={folder} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
