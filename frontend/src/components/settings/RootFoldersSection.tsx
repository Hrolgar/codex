import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getRootFolders,
  addRootFolder,
  deleteRootFolder,
  type RootFolder,
} from "@/api/client";
import { Trash2, Plus, Loader2, FolderOpen, HardDrive } from "lucide-react";

function formatBytes(bytes: number) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

const MEDIA_TYPES = ["book", "audiobook", "ebook", "comic", "magazine"];

export default function RootFoldersSection() {
  const queryClient = useQueryClient();
  const [path, setPath] = useState("");
  const [mediaType, setMediaType] = useState("book");
  const [isDefault, setIsDefault] = useState(false);

  const { data: folders = [], isLoading } = useQuery({
    queryKey: ["root-folders"],
    queryFn: getRootFolders,
  });

  const addMutation = useMutation({
    mutationFn: addRootFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["root-folders"] });
      setPath("");
      setMediaType("book");
      setIsDefault(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteRootFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["root-folders"] });
    },
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!path.trim()) return;
    addMutation.mutate({
      path: path.trim(),
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
            const usedSpace = folder.total_space - folder.free_space;
            const usedPct =
              folder.total_space > 0
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
                      {folder.total_space > 0 && (
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
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => deleteMutation.mutate(folder.id)}
                    disabled={deleteMutation.isPending}
                    className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors flex-shrink-0"
                    title="Delete root folder"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
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
          <input
            type="text"
            placeholder="/path/to/media"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="flex-1 min-w-[200px] px-3 py-2 text-sm bg-gray-900 border border-gray-700 rounded-md text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
          />
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
    </div>
  );
}
