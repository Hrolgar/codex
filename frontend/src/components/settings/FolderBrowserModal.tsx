import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { browseFolders } from "@/api/client";
import { FolderOpen, ArrowUp, Loader2, X } from "lucide-react";

interface FolderBrowserModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
  initialPath?: string;
}

export default function FolderBrowserModal({
  open,
  onClose,
  onSelect,
  initialPath,
}: FolderBrowserModalProps) {
  const [currentPath, setCurrentPath] = useState(initialPath || "");

  useEffect(() => {
    if (open) setCurrentPath(initialPath || "");
  }, [open, initialPath]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["browse-folders", currentPath],
    queryFn: () => browseFolders(currentPath || undefined),
    enabled: open,
  });

  const handleSelect = useCallback(() => {
    if (data?.current_path) {
      onSelect(data.current_path);
      onClose();
    }
  }, [data, onSelect, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-lg w-full max-w-lg mx-4 flex flex-col max-h-[80vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <h3 className="text-sm font-semibold text-gray-100">Browse Folders</h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-gray-300 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Current path */}
        <div className="px-4 py-2 border-b border-gray-700/50 flex items-center gap-2">
          {data?.parent != null && (
            <button
              onClick={() => setCurrentPath(data.parent!)}
              className="p-1 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors flex-shrink-0"
              title="Go to parent directory"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          )}
          <span className="text-xs text-gray-400 truncate font-mono">
            {data?.current_path || currentPath || "/"}
          </span>
        </div>

        {/* Directory listing */}
        <div className="flex-1 overflow-y-auto min-h-[200px]">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-gray-400">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              Loading...
            </div>
          ) : isError ? (
            <div className="text-center py-12 text-red-400 text-sm">
              Failed to browse directory
            </div>
          ) : data?.directories.length === 0 ? (
            <div className="text-center py-12 text-gray-500 text-sm">
              No subdirectories
            </div>
          ) : (
            <div className="py-1">
              {data?.directories.map((dir) => (
                <button
                  key={dir.path}
                  onClick={() => setCurrentPath(dir.path)}
                  className="w-full flex items-center gap-3 px-4 py-2 text-left bg-gray-800/50 hover:bg-gray-700 transition-colors text-sm text-gray-200"
                >
                  <FolderOpen className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  <span className="truncate">{dir.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 rounded-md transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSelect}
            disabled={!data?.current_path}
            className="px-4 py-1.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-md transition-colors"
          >
            Select
          </button>
        </div>
      </div>
    </div>
  );
}
