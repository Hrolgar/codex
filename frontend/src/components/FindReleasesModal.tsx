import { useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { searchExternal, createDownload } from "@/api/client";
import type { SearchResult } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import { X, Download, Loader2, Search } from "lucide-react";

interface FindReleasesModalProps {
  open: boolean;
  onClose: () => void;
  bookTitle: string;
  bookAuthor?: string;
}

function formatSize(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(1)} GB`;
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

export default function FindReleasesModal({
  open,
  onClose,
  bookTitle,
  bookAuthor,
}: FindReleasesModalProps) {
  const { addToast } = useToast();
  const searchQuery = [bookTitle, bookAuthor].filter(Boolean).join(" ");

  const {
    data: results,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["search-releases", searchQuery],
    queryFn: () => searchExternal(searchQuery),
    enabled: open && !!searchQuery,
  });

  useEffect(() => {
    if (open && searchQuery) {
      refetch();
    }
  }, [open, searchQuery, refetch]);

  const downloadMutation = useMutation({
    mutationFn: (result: SearchResult) =>
      createDownload({
        source_url: result.download_url!,
        source_type: result.source ?? "unknown",
      }),
    onSuccess: () => addToast("Download started"),
    onError: () => addToast("Failed to start download", "error"),
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-4xl max-h-[80vh] flex flex-col p-6">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-200 transition-colors"
        >
          <X size={18} />
        </button>

        <h2 className="text-lg font-semibold text-gray-100 mb-1 flex items-center gap-2">
          <Search size={18} />
          Find Releases
        </h2>
        <p className="text-sm text-gray-400 mb-4 truncate">
          Searching for: {searchQuery}
        </p>

        <div className="flex-1 overflow-auto min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-gray-400" />
              <span className="ml-2 text-gray-400">Searching...</span>
            </div>
          ) : !results || results.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Search size={32} className="text-gray-700 mb-3" />
              <p className="text-gray-400">No results found</p>
              <p className="text-sm text-gray-500 mt-1">
                Try adjusting your search terms
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  <th className="pb-2 pr-4 font-medium">Title</th>
                  <th className="pb-2 pr-4 font-medium">Indexer</th>
                  <th className="pb-2 pr-4 font-medium">Size</th>
                  <th className="pb-2 pr-4 font-medium">Seeders</th>
                  <th className="pb-2 pr-4 font-medium">Format</th>
                  <th className="pb-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {results.map((result, idx) => (
                  <tr
                    key={`${result.title}-${idx}`}
                    className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
                  >
                    <td className="py-2.5 pr-4 text-gray-200 max-w-xs truncate">
                      {result.title}
                    </td>
                    <td className="py-2.5 pr-4 text-gray-400">
                      {result.indexer ?? "—"}
                    </td>
                    <td className="py-2.5 pr-4 text-gray-400 whitespace-nowrap">
                      {formatSize(result.size)}
                    </td>
                    <td className="py-2.5 pr-4 text-gray-400">
                      {result.seeders ?? "—"}
                    </td>
                    <td className="py-2.5 pr-4 text-gray-400 uppercase">
                      {result.format ?? "—"}
                    </td>
                    <td className="py-2.5">
                      <button
                        onClick={() => downloadMutation.mutate(result)}
                        disabled={
                          !result.download_url || downloadMutation.isPending
                        }
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                      >
                        {downloadMutation.isPending ? (
                          <Loader2 size={12} className="animate-spin" />
                        ) : (
                          <Download size={12} />
                        )}
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
