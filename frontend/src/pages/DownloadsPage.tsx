import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getDownloads,
  deleteDownload,
  retryDownload,
} from "@/api/client";
import type { DownloadResponse } from "@/api/client";
import { useDownloadProgress } from "@/hooks/useDownloadProgress";
import {
  Download,
  Trash2,
  RefreshCw,
  Check,
  AlertCircle,
  Loader2,
  Inbox,
  Clock,
} from "lucide-react";

type StatusFilter = "all" | "active" | "complete" | "failed";

export default function DownloadsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const queryClient = useQueryClient();

  // Live WebSocket updates
  useDownloadProgress();

  const apiStatus = statusFilter === "active"
    ? "downloading"
    : statusFilter === "all"
      ? undefined
      : statusFilter === "complete"
        ? "complete"
        : "error";

  const { data: downloads, isLoading, isError } = useQuery({
    queryKey: ["downloads", apiStatus],
    queryFn: () => getDownloads(apiStatus),
    refetchInterval: 10_000,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDownload,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["downloads"] }),
  });

  const retryMutation = useMutation({
    mutationFn: retryDownload,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["downloads"] }),
  });

  // For "active" tab, also include pending
  const filtered = downloads
    ? statusFilter === "active"
      ? downloads.filter(
          (d) => d.status === "downloading" || d.status === "pending"
        )
      : downloads
    : [];

  // Sort newest first
  const sorted = [...filtered].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const tabs: { value: StatusFilter; label: string }[] = [
    { value: "all", label: "All" },
    { value: "active", label: "Active" },
    { value: "complete", label: "Complete" },
    { value: "failed", label: "Failed" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Downloads</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Manage your download queue
        </p>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-3 py-1 rounded text-sm transition-colors ${
              statusFilter === tab.value
                ? "bg-indigo-500 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 size={24} className="text-indigo-400 animate-spin mb-3" />
          <p className="text-sm text-gray-500">Loading downloads...</p>
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle size={24} className="text-red-400 mb-3" />
          <p className="text-sm text-red-400">
            Failed to load downloads. Please try again.
          </p>
        </div>
      ) : sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gray-800/50 flex items-center justify-center mb-5">
            <Inbox size={28} className="text-gray-600" />
          </div>
          <h3 className="text-lg font-medium text-gray-300 mb-2">
            No downloads
          </h3>
          <p className="text-sm text-gray-500 max-w-xs">
            {statusFilter === "all"
              ? "Search for books and download them to see them here."
              : `No ${statusFilter} downloads.`}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {sorted.map((dl) => (
            <DownloadItem
              key={dl.id}
              download={dl}
              onDelete={(id) => deleteMutation.mutate(id)}
              onRetry={(id) => retryMutation.mutate(id)}
              isDeleting={
                deleteMutation.isPending &&
                deleteMutation.variables === dl.id
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}

function DownloadItem({
  download,
  onDelete,
  onRetry,
  isDeleting,
}: {
  download: DownloadResponse;
  onDelete: (id: string) => void;
  onRetry: (id: string) => void;
  isDeleting: boolean;
}) {
  const filename =
    download.target_path?.split("/").pop() ??
    download.source_url.split("/").pop() ??
    "Unknown file";

  const statusConfig: Record<
    string,
    { color: string; icon: React.ReactNode; label: string }
  > = {
    pending: {
      color: "text-gray-400",
      icon: <Clock size={14} />,
      label: "Pending",
    },
    downloading: {
      color: "text-indigo-400",
      icon: <Loader2 size={14} className="animate-spin" />,
      label: "Downloading",
    },
    complete: {
      color: "text-green-400",
      icon: <Check size={14} />,
      label: "Complete",
    },
    error: {
      color: "text-red-400",
      icon: <AlertCircle size={14} />,
      label: "Error",
    },
  };

  const status = statusConfig[download.status] ?? statusConfig.pending;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Download size={14} className="text-gray-500" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-medium text-gray-100 truncate">
              {filename}
            </h3>
            <span className="rounded-full px-2 py-0.5 text-xs bg-gray-700 text-gray-300 flex-shrink-0">
              {download.source_type}
            </span>
          </div>

          {/* Status */}
          <div className={`flex items-center gap-1.5 text-xs ${status.color}`}>
            {status.icon}
            <span>{status.label}</span>
            {download.status === "downloading" && (
              <span className="text-gray-500 ml-1">
                {Math.round(download.progress)}%
              </span>
            )}
          </div>

          {/* Progress bar for downloading */}
          {download.status === "downloading" && (
            <div className="mt-2 h-1.5 rounded-full bg-gray-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${download.progress}%` }}
              />
            </div>
          )}

          {/* Error message */}
          {download.status === "error" && download.error && (
            <p className="text-xs text-red-400/70 mt-1 truncate">
              {download.error}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {download.status === "error" && (
            <button
              onClick={() => onRetry(download.id)}
              className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-400 hover:bg-gray-800 transition-colors"
              title="Retry"
            >
              <RefreshCw size={14} />
            </button>
          )}
          <button
            onClick={() => onDelete(download.id)}
            disabled={isDeleting}
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-gray-800 transition-colors disabled:opacity-50"
            title="Delete"
          >
            {isDeleting ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Trash2 size={14} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
