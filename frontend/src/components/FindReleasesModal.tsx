import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { searchExternal, createDownload } from "@/api/client";
import type { SearchResult } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import { X, Download, Loader2, Search, ArrowDown, ArrowUp } from "lucide-react";

interface FindReleasesModalProps {
  open: boolean;
  onClose: () => void;
  bookTitle: string;
  bookAuthor?: string;
}

function formatSize(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(1)} GB`;
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(0)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

function parseFormat(title: string, format: string | null): string {
  if (format) return format.toLowerCase();
  const match = title.match(/\.(epub|mobi|azw3?|pdf|cbz|cbr|m4b|mp3|flac)\b/i);
  return match ? match[1].toLowerCase() : "—";
}

type SortKey = "size" | "seeders" | "title" | "indexer" | "format";
type SortDir = "asc" | "desc";

const TABS = [
  { id: "prowlarr", label: "Prowlarr", enabled: true },
  { id: "direct", label: "Direct Download", enabled: false },
] as const;

export default function FindReleasesModal({
  open,
  onClose,
  bookTitle,
  bookAuthor,
}: FindReleasesModalProps) {
  const { addToast } = useToast();
  const searchQuery = [bookTitle, bookAuthor].filter(Boolean).join(" ");

  const [activeTab, setActiveTab] = useState("prowlarr");
  const [filter, setFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("seeders");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

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

  useEffect(() => {
    if (open) {
      setFilter("");
      setSortKey("seeders");
      setSortDir("desc");
    }
  }, [open]);

  const downloadMutation = useMutation({
    mutationFn: (result: SearchResult) =>
      createDownload({
        source_url: result.download_url!,
        source_type: result.source ?? "unknown",
      }),
    onSuccess: () => addToast("Download started"),
    onError: () => addToast("Failed to start download", "error"),
  });

  const filtered = useMemo(() => {
    if (!results) return [];
    let items = results;
    if (filter.trim()) {
      const q = filter.toLowerCase();
      items = items.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          (r.indexer ?? "").toLowerCase().includes(q) ||
          parseFormat(r.title, r.format).includes(q),
      );
    }
    return [...items].sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      switch (sortKey) {
        case "size":
          return ((a.size ?? 0) - (b.size ?? 0)) * dir;
        case "seeders":
          return ((a.seeders ?? 0) - (b.seeders ?? 0)) * dir;
        case "title":
          return a.title.localeCompare(b.title) * dir;
        case "indexer":
          return (a.indexer ?? "").localeCompare(b.indexer ?? "") * dir;
        case "format":
          return parseFormat(a.title, a.format).localeCompare(
            parseFormat(b.title, b.format),
          ) * dir;
        default:
          return 0;
      }
    });
  }, [results, filter, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "title" || key === "indexer" || key === "format" ? "asc" : "desc");
    }
  }

  function SortIcon({ column }: { column: SortKey }) {
    if (sortKey !== column)
      return <span className="ml-1 text-gray-600 text-xs">⇅</span>;
    return sortDir === "asc" ? (
      <ArrowUp size={12} className="ml-1 inline text-indigo-400" />
    ) : (
      <ArrowDown size={12} className="ml-1 inline text-indigo-400" />
    );
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-6xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 px-6 pt-5 pb-0">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-200 transition-colors"
          >
            <X size={18} />
          </button>

          <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
            <Search size={18} />
            Find Releases
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
            Searching for: <span className="text-gray-300">{searchQuery}</span>
          </p>

          {/* Tabs */}
          <div className="flex gap-1 mt-4 border-b border-gray-800">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                disabled={!tab.enabled}
                onClick={() => tab.enabled && setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-indigo-500 text-indigo-400"
                    : tab.enabled
                      ? "border-transparent text-gray-400 hover:text-gray-200"
                      : "border-transparent text-gray-600 cursor-not-allowed"
                }`}
              >
                {tab.label}
                {!tab.enabled && (
                  <span className="ml-1.5 text-[10px] bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded-full">
                    soon
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Search filter + count */}
          <div className="flex items-center gap-3 mt-4 mb-3">
            <div className="relative flex-1">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
              />
              <input
                type="text"
                placeholder="Filter results..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
              />
            </div>
            {results && (
              <span className="text-xs text-gray-500 whitespace-nowrap">
                {filtered.length} of {results.length} results
              </span>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto min-h-0 px-6 pb-5">
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
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-gray-400">No results match your filter</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-900">
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  <th
                    className="pb-2 pr-3 font-medium cursor-pointer hover:text-gray-300 select-none"
                    onClick={() => toggleSort("title")}
                  >
                    Title <SortIcon column="title" />
                  </th>
                  <th
                    className="pb-2 pr-3 font-medium cursor-pointer hover:text-gray-300 select-none whitespace-nowrap"
                    onClick={() => toggleSort("indexer")}
                  >
                    Indexer <SortIcon column="indexer" />
                  </th>
                  <th
                    className="pb-2 pr-3 font-medium cursor-pointer hover:text-gray-300 select-none whitespace-nowrap"
                    onClick={() => toggleSort("size")}
                  >
                    Size <SortIcon column="size" />
                  </th>
                  <th
                    className="pb-2 pr-3 font-medium cursor-pointer hover:text-gray-300 select-none whitespace-nowrap"
                    onClick={() => toggleSort("format")}
                  >
                    Format <SortIcon column="format" />
                  </th>
                  <th
                    className="pb-2 pr-3 font-medium cursor-pointer hover:text-gray-300 select-none whitespace-nowrap"
                    onClick={() => toggleSort("seeders")}
                  >
                    S / L <SortIcon column="seeders" />
                  </th>
                  <th className="pb-2 font-medium w-10" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((result, idx) => (
                  <tr
                    key={`${result.title}-${idx}`}
                    className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors group"
                  >
                    <td className="py-2.5 pr-3 text-gray-200">
                      <span className="break-words">{result.title}</span>
                    </td>
                    <td className="py-2.5 pr-3 text-gray-400 whitespace-nowrap">
                      {result.indexer ?? "—"}
                    </td>
                    <td className="py-2.5 pr-3 text-gray-400 whitespace-nowrap">
                      {formatSize(result.size)}
                    </td>
                    <td className="py-2.5 pr-3 whitespace-nowrap">
                      <span className="inline-block bg-gray-800 text-gray-300 text-xs px-2 py-0.5 rounded uppercase">
                        {parseFormat(result.title, result.format)}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-gray-400 whitespace-nowrap">
                      <span className="text-green-400">{result.seeders ?? "—"}</span>
                      {" / "}
                      <span className="text-red-400">—</span>
                    </td>
                    <td className="py-2.5">
                      <button
                        onClick={() => downloadMutation.mutate(result)}
                        disabled={
                          !result.download_url || downloadMutation.isPending
                        }
                        title="Download"
                        className="inline-flex items-center justify-center w-8 h-8 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                      >
                        {downloadMutation.isPending ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Download size={14} />
                        )}
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
