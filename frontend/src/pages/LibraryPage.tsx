import { useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getBooks, toggleBookMonitored } from "@/api/client";
import type { BookListItem } from "@/api/client";
import { BookOpen, ChevronLeft, ChevronRight, Settings as SettingsIcon, ArrowUpDown, Eye, EyeOff, Trash2 } from "lucide-react";
import BookGrid from "@/components/library/BookGrid";
import SearchBar from "@/components/library/SearchBar";
import BulkActionBar from "@/components/BulkActionBar";
import type { BulkAction } from "@/components/BulkActionBar";
import { useToast } from "@/contexts/ToastContext";

type SortOption = "title" | "author" | "date";

interface LibraryPageProps {
  initialMediaType?: string;
  title?: string;
}

export default function LibraryPage({ initialMediaType = "", title = "Library" }: LibraryPageProps) {
  const [search, setSearch] = useState("");
  const [mediaType, setMediaType] = useState(initialMediaType);
  const [sortBy, setSortBy] = useState<SortOption>("title");
  const [page, setPage] = useState(1);
  const [selectedBookIds, setSelectedBookIds] = useState<Set<string>>(new Set());
  const perPage = 24;
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const { data, isLoading } = useQuery({
    queryKey: ["books", search, mediaType, page],
    queryFn: () =>
      getBooks({
        search: search || undefined,
        media_type: mediaType || undefined,
        page,
        per_page: perPage,
      }),
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);
  const handleMediaType = useCallback((t: string) => {
    setMediaType(t);
    setPage(1);
  }, []);

  const totalPages = data ? Math.ceil(data.total / perPage) : 0;

  const sortedBooks = useMemo(() => {
    let items: BookListItem[] = data?.items ?? [];
    return [...items].sort((a, b) => {
      switch (sortBy) {
        case "author": return (a.author ?? "").localeCompare(b.author ?? "");
        case "date": return (b.publish_year ?? 0) - (a.publish_year ?? 0);
        default: return (a.title ?? "").localeCompare(b.title ?? "");
      }
    });
  }, [data?.items, sortBy]);

  const toggleSelected = useCallback((bookId: string) => {
    setSelectedBookIds((prev) => {
      const next = new Set(prev);
      if (next.has(bookId)) next.delete(bookId);
      else next.add(bookId);
      return next;
    });
  }, []);

  const bulkMonitor = useCallback(async (monitored: boolean) => {
    try {
      await Promise.all(
        Array.from(selectedBookIds).map((bookId) => toggleBookMonitored(bookId, monitored))
      );
      queryClient.invalidateQueries({ queryKey: ["books"] });
      addToast(monitored ? "Books set to monitored" : "Books set to unmonitored", "info");
      setSelectedBookIds(new Set());
    } catch {
      addToast("Failed to update some books", "error");
    }
  }, [selectedBookIds, queryClient, addToast]);

  const bulkActions: BulkAction[] = [
    { label: "Monitor Selected", icon: Eye, onClick: () => bulkMonitor(true) },
    { label: "Unmonitor Selected", icon: EyeOff, onClick: () => bulkMonitor(false) },
    { label: "Delete Selected", icon: Trash2, onClick: () => addToast("Delete not yet implemented", "info"), variant: "danger" },
  ];

  // Empty library state
  if (!isLoading && data?.total === 0 && !search && !mediaType) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-20 h-20 rounded-2xl bg-gray-800/50 flex items-center justify-center mb-6">
          <BookOpen size={36} className="text-gray-600" />
        </div>
        <h2 className="text-xl font-semibold text-gray-200 mb-2">
          Your library is empty
        </h2>
        <p className="text-sm text-gray-500 max-w-sm mb-8">
          Add a library source in Settings to scan your books.
        </p>
        <Link
          to="/settings"
          className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2"
        >
          <SettingsIcon size={14} />
          Settings
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">{title}</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {data
              ? `${data.total.toLocaleString()} item${data.total !== 1 ? "s" : ""}`
              : "Loading..."}
          </p>
        </div>
      </div>

      <SearchBar
        onSearch={handleSearch}
        onMediaTypeChange={handleMediaType}
        mediaType={mediaType}
      />

      {/* Sort */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <ArrowUpDown size={14} className="text-gray-500" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-indigo-500 transition-colors"
          >
            <option value="title">Sort by Title</option>
            <option value="author">Sort by Author</option>
            <option value="date">Sort by Publication Year</option>
          </select>
        </div>
      </div>

      <BookGrid
        books={sortedBooks}
        isLoading={isLoading}
        selectedBookIds={selectedBookIds}
        onToggleSelected={toggleSelected}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
          >
            <ChevronLeft size={18} />
          </button>
          <span className="text-sm text-gray-400 px-3">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      )}

      <BulkActionBar
        selectedCount={selectedBookIds.size}
        onClearSelection={() => setSelectedBookIds(new Set())}
        actions={bulkActions}
      />

      {/* Bottom padding when bulk bar is visible */}
      {selectedBookIds.size > 0 && <div className="h-16" />}
    </div>
  );
}
