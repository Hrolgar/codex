import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getRootFolders,
  addRootFolder,
  deleteRootFolder,
  scanRootFolder,
  type RootFolder,
} from "@/api/client";
import { Trash2, Plus, Loader2, FolderOpen, HardDrive, Search, RefreshCw } from "lucide-react";
import FolderBrowserModal from "./FolderBrowserModal";

function formatBytes(bytes: number) {
  if (bytes == null || isNaN(bytes)) return "Unknown";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const MEDIA_TYPES = ["ebook", "audiobook", "comic"];

export default function RootFoldersSection() {
  const queryClient = useQueryClient();
  const [path, setPath] = useState("");
  const [mediaType, setMediaType] = useState("ebook");
  const [isDefault, setIsDefault] = useState(false);
  const [browseOpen, setBrowseOpen] = useState(false);

  const { data: folders = [], isLoading } = useQuery({
    queryKey: ["root-folders"],
    queryFn: getRootFolders,
  });

  const addMutation = useMutation({
    mutationFn: addRootFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["root-folders"] });
      setPath("");
      setMediaType("ebook");
      setIsDefault(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteRootFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["root-folders"] });
    },
  });

  const scanMutation = useMutation({
    mutationFn: scanRootFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["root-folders"] });
    },
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!path.trim()) return;
    const trimmedPath = path.trim();
    const name = trimmedPath.split("/").filter(Boolean).pop() || trimmedPath;
    addMutation.mutate({
      path: trimmedPath,
      name,
      media_type: mediaType,
      default: isDefault,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-100">Root Folders</h2>
        <p className="text-sm text-gray-400 mt-1">
          Directories where media files are stored and organized.
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12 text-gray-400">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading...
        </div>
      ) : folders.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <HardDrive className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p>No root folders configured</p>
        </div>
      ) : (
        <div className="space-y-2">
          {folders.map((folder: RootFolder) => {
            const hasSpace = folder.total_space != null && folder.free_space != null && folder.total_space > 0;
            const usedSpace = hasSpace ? folder.total_space - folder.free_space : 0;
            const usedPct = hasSpace
              ? Math.round((usedSpace / folder.total_space) * 100)
              : 0;

            return (
              <div
                key={folder.id}
                className="bg-gray-800/50 border border-gray-700 rounded-lg p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <FolderOpen className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-100 truncate">
                          {folder.name || folder.path}
                        </span>
                        <span className="px-1.5 py-0.5 text-[10px] font-medium uppercase rounded bg-indigo-500/20 text-indigo-300 flex-shrink-0">
                          {folder.media_type}
                        </span>
                        {folder.default && (
                          <span className="px-1.5 py-0.5 text-[10px] font-medium uppercase rounded bg-green-500/20 text-green-300 flex-shrink-0">
                            default
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">
                        {folder.path}
                      </p>
                      {hasSpace ? (
                        <div className="mt-2">
                          <div className="flex items-center gap-2 text-[11px] text-gray-400 mb-1">
                            <span>
                              {formatBytes(usedSpace)} / {formatBytes(folder.total_space)} used
                            </span>
                            <span>({usedPct}%)</span>
                          </div>
                          <div className="w-48 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                usedPct > 90
                                  ? "bg-red-500"
                                  : usedPct > 70
                                    ? "bg-yellow-500"
                                    : "bg-indigo-500"
                              }`}
                              style={{ width: `${usedPct}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <p className="text-[11px] text-gray-500 mt-1">Disk space: Unknown</p>
                      )}
                      {folder.last_scan_at && (
                        <p className="text-[11px] text-gray-500 mt-1">
                          Last scanned {timeAgo(folder.last_scan_at)}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {folder.scan_status === "scanning" && (
                      <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" title="Scanning" />
                    )}
                    {folder.scan_status === "error" && (
                      <span className="w-2 h-2 rounded-full bg-red-500 inline-block" title="Scan error" />
                    )}
                    <button
                      onClick={() => scanMutation.mutate(folder.id)}
                      disabled={scanMutation.isPending || folder.scan_status === "scanning"}
                      className="p-1.5 text-gray-500 hover:text-indigo-400 hover:bg-indigo-500/10 rounded transition-colors"
                      title="Scan folder"
                    >
                      <RefreshCw className={`w-4 h-4 ${scanMutation.isPending && scanMutation.variables === folder.id ? "animate-spin" : ""}`} />
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(folder.id)}
                      disabled={deleteMutation.isPending}
                      className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                      title="Delete root folder"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add form */}
      <form
        onSubmit={handleAdd}
        className="bg-gray-800/30 border border-gray-700 rounded-lg p-4 space-y-3"
      >
        <h3 className="text-sm font-medium text-gray-300">Add Root Folder</h3>
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-[200px] flex gap-1.5">
            <input
              type="text"
              placeholder="/path/to/media"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              className="flex-1 px-3 py-2 text-sm bg-gray-900 border border-gray-700 rounded-md text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="button"
              onClick={() => setBrowseOpen(true)}
              className="px-2.5 py-2 text-sm bg-gray-800 border border-gray-700 rounded-md text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors flex-shrink-0"
              title="Browse folders"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
          <select
            value={mediaType}
            onChange={(e) => setMediaType(e.target.value)}
            className="px-3 py-2 text-sm bg-gray-900 border border-gray-700 rounded-md text-gray-100 focus:outline-none focus:border-indigo-500"
          >
            {MEDIA_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              className="rounded border-gray-600 bg-gray-900 text-indigo-500 focus:ring-indigo-500"
            />
            Set as default
          </label>
          <button
            type="submit"
            disabled={!path.trim() || addMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-md transition-colors"
          >
            {addMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Plus className="w-3.5 h-3.5" />
            )}
            Add
          </button>
        </div>
        {addMutation.isError && (
          <p className="text-xs text-red-400">
            {(addMutation.error as Error).message}
          </p>
        )}
      </form>

      <FolderBrowserModal
        open={browseOpen}
        onClose={() => setBrowseOpen(false)}
        onSelect={(selected) => setPath(selected)}
        initialPath={path || undefined}
      />
    </div>
  );
}
