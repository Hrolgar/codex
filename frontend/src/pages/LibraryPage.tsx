import { useCallback, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getBooks, seedDemoData } from "@/api/client";
import type { BookListItem } from "@/api/client";
import { BookOpen, ChevronLeft, ChevronRight, Settings as SettingsIcon, ArrowUpDown } from "lucide-react";
import BookGrid from "@/components/library/BookGrid";
import SearchBar from "@/components/library/SearchBar";

type SortOption = "title" | "author" | "date" | "status";

interface LibraryPageProps {
  initialMediaType?: string;
  title?: string;
}

export default function LibraryPage({ initialMediaType = "", title = "Library" }: LibraryPageProps) {
  const queryClient = useQueryClient();
  const seedMutation = useMutation({
    mutationFn: seedDemoData,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["books"] }),
  });
  const [search, setSearch] = useState("");
  const [mediaType, setMediaType] = useState(initialMediaType);
  const [readFilter, setReadFilter] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("title");
  const [page, setPage] = useState(1);
  const perPage = 24;

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
    const statusOrder: Record<string, number> = { reading: 0, unread: 1, read: 2 };
    let items: BookListItem[] = data?.items ?? [];
    if (readFilter) {
      items = items.filter((b) => (b.reading_status ?? "unread") === readFilter);
    }
    return [...items].sort((a, b) => {
      switch (sortBy) {
        case "author": return (a.author ?? "").localeCompare(b.author ?? "");
        case "date": return (b.publish_year ?? 0) - (a.publish_year ?? 0);
        case "status": return (statusOrder[a.reading_status ?? "unread"] ?? 1) - (statusOrder[b.reading_status ?? "unread"] ?? 1);
        default: return (a.title ?? "").localeCompare(b.title ?? "");
      }
    });
  }, [data?.items, readFilter, sortBy]);

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
          Add a library source in Settings to scan your books, or seed some demo
          data to explore the interface.
        </p>
        <div className="flex gap-3">
          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="px-4 py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            {seedMutation.isPending ? "Seeding..." : "Seed Demo Data"}
          </button>
          <Link
            to="/settings"
            className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2"
          >
            <SettingsIcon size={14} />
            Settings
          </Link>
        </div>
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
        <button
          onClick={() => seedMutation.mutate()}
          disabled={seedMutation.isPending}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {seedMutation.isPending ? "Seeding..." : "Seed Demo Data"}
        </button>
      </div>

      <SearchBar
        onSearch={handleSearch}
        onMediaTypeChange={handleMediaType}
        mediaType={mediaType}
      />

      {/* Read status filter + sort */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
          {[
            { value: "", label: "All" },
            { value: "reading", label: "Reading" },
            { value: "read", label: "Read" },
            { value: "unread", label: "Unread" },
          ].map((f) => (
            <button
              key={f.value}
              onClick={() => { setReadFilter(f.value); setPage(1); }}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                readFilter === f.value
                  ? "bg-indigo-500 text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <ArrowUpDown size={14} className="text-gray-500" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-indigo-500 transition-colors"
          >
            <option value="title">Sort by Title</option>
            <option value="author">Sort by Author</option>
            <option value="date">Sort by Date Added</option>
            <option value="status">Sort by Read Status</option>
          </select>
        </div>
      </div>

      <BookGrid
        books={sortedBooks}
        isLoading={isLoading}
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
    </div>
  );
}
