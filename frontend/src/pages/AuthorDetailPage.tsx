import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAuthor, refreshAuthor, deleteAuthor, getSeriesDetail } from "@/api/client";
import type { BookListItem } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import {
  ArrowLeft,
  BookOpen,
  RefreshCw,
  Trash2,
  User,
  Check,
  X,
  Search,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertCircle,
  Eye,
  EyeOff,
} from "lucide-react";

export default function AuthorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [collapsedSeries, setCollapsedSeries] = useState<Set<string>>(new Set());
  const [bioExpanded, setBioExpanded] = useState(false);
  const { data: author, isLoading, error } = useQuery({
    queryKey: ["author", id],
    queryFn: () => getAuthor(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.catalog_status === "fetching") return 3000;
      return false;
    },
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshAuthor(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["author", id] });
      addToast("Refreshing catalog...", "info");
    },
    onError: () => {
      addToast("Failed to refresh catalog", "error");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (removeBooks: boolean) => deleteAuthor(id!, removeBooks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authors"] });
      addToast("Author deleted");
      navigate("/");
    },
  });

  const toggleSeries = (seriesId: string) => {
    setCollapsedSeries((prev) => {
      const next = new Set(prev);
      if (next.has(seriesId)) next.delete(seriesId);
      else next.add(seriesId);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-4 w-24 skeleton rounded" />
        <div className="flex gap-6">
          <div className="w-32 h-32 skeleton rounded-lg shrink-0" />
          <div className="space-y-3 flex-1">
            <div className="h-8 w-48 skeleton rounded" />
            <div className="h-4 w-full skeleton rounded" />
            <div className="h-4 w-3/4 skeleton rounded" />
          </div>
        </div>
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 skeleton rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !author) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <User size={32} className="text-gray-700 mb-3" />
        <p className="text-gray-400 text-lg">Author not found</p>
        <Link
          to="/"
          className="text-indigo-400 hover:text-indigo-300 text-sm mt-2 inline-block"
        >
          Back to authors
        </Link>
      </div>
    );
  }

  const isFetching = author.catalog_status === "fetching";
  const isCatalogError = author.catalog_status === "error";

  const totalSeriesBooks = author.series.reduce((sum, s) => sum + s.book_count, 0);
  const ownedSeriesBooks = author.series.reduce((sum, s) => sum + s.owned_count, 0);
  const totalStandalone = author.standalone_books.length;
  const ownedStandalone = author.standalone_books.filter((b) => b.owned).length;
  const totalBooks = totalSeriesBooks + totalStandalone;
  const ownedBooks = ownedSeriesBooks + ownedStandalone;
  const missingBooks = totalBooks - ownedBooks;

  return (
    <div className="space-y-8">
      {/* Back link */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors"
      >
        <ArrowLeft size={16} />
        Back to authors
      </Link>

      {/* Header */}
      <div className="flex gap-6">
        {/* Photo */}
        <div className="w-32 h-32 rounded-lg bg-gray-800 overflow-hidden shrink-0 flex items-center justify-center">
          {author.photo_url ? (
            <img
              src={author.photo_url}
              alt={author.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <User size={48} className="text-gray-600" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-gray-100">{author.name}</h1>
              {/* Book count summary */}
              <p className="text-sm text-gray-400 mt-1">
                {totalBooks} book{totalBooks !== 1 ? "s" : ""}, {ownedBooks} owned
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {/* Monitor toggle */}
              <button
                onClick={() => {
                  // Toggle monitored status via refresh (backend handles it)
                  addToast(
                    author.monitored
                      ? "Monitoring paused"
                      : "Monitoring all books",
                    "info"
                  );
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  author.monitored
                    ? "text-green-400 bg-green-500/10 hover:bg-green-500/20"
                    : "text-gray-400 bg-gray-800 hover:bg-gray-700"
                }`}
                title={author.monitored ? "Monitoring enabled" : "Monitoring disabled"}
              >
                {author.monitored ? <Eye size={14} /> : <EyeOff size={14} />}
                {author.monitored ? "Monitored" : "Monitor"}
              </button>
              <button
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw
                  size={14}
                  className={refreshMutation.isPending ? "animate-spin" : ""}
                />
                Refresh
              </button>
              {showDeleteConfirm ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-red-400">Remove books too?</span>
                  <button
                    onClick={() => deleteMutation.mutate(true)}
                    disabled={deleteMutation.isPending}
                    className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors"
                  >
                    {deleteMutation.isPending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      "Remove Books"
                    )}
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(false)}
                    disabled={deleteMutation.isPending}
                    className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    Keep Books
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              )}
            </div>
          </div>

          {/* Bio - expandable */}
          {author.bio && (
            <div className="mt-3 bg-gray-900/50 rounded-lg p-3">
              <p
                className={`text-sm text-gray-400 leading-relaxed ${
                  !bioExpanded ? "line-clamp-3" : ""
                }`}
              >
                {author.bio}
              </p>
              {author.bio.length > 200 && (
                <button
                  onClick={() => setBioExpanded(!bioExpanded)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 mt-1.5 transition-colors"
                >
                  {bioExpanded ? "Show less" : "Show more"}
                </button>
              )}
            </div>
          )}

          {/* Stats bar */}
          <div className="flex items-center gap-4 mt-3">
            <span className="text-sm text-gray-300">
              <span className="font-semibold text-gray-100">{totalBooks}</span>{" "}
              total
            </span>
            <span className="text-sm text-green-400">
              <span className="font-semibold">{ownedBooks}</span> owned
            </span>
            {missingBooks > 0 && (
              <span className="text-sm text-gray-500">
                <span className="font-semibold">{missingBooks}</span> missing
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Catalog status banner */}
      {isFetching && (
        <div className="flex items-center gap-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg px-4 py-3">
          <Loader2 size={18} className="text-indigo-400 animate-spin shrink-0" />
          <div>
            <p className="text-sm font-medium text-indigo-400">
              Fetching bibliography from OpenLibrary...
            </p>
            <p className="text-xs text-indigo-400/70 mt-0.5">
              This may take a minute for prolific authors.
            </p>
          </div>
        </div>
      )}

      {isCatalogError && (
        <div className="flex items-center justify-between bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          <div className="flex items-center gap-3">
            <AlertCircle size={18} className="text-red-400 shrink-0" />
            <p className="text-sm text-red-400">
              Failed to fetch catalog from OpenLibrary.
            </p>
          </div>
          <button
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors"
          >
            <RefreshCw
              size={14}
              className={refreshMutation.isPending ? "animate-spin" : ""}
            />
            Retry
          </button>
        </div>
      )}

      {/* Series sections with inline completion progress */}
      {author.series.map((series) => {
        const isCollapsed = collapsedSeries.has(series.id);
        const seriesPct = series.book_count > 0
          ? Math.round((series.owned_count / series.book_count) * 100)
          : 0;
        return (
          <section key={series.id}>
            <button
              onClick={() => toggleSeries(series.id)}
              className="w-full flex items-center justify-between bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 hover:border-gray-700 transition-colors"
            >
              <div className="flex items-center gap-3">
                {isCollapsed ? (
                  <ChevronRight size={16} className="text-gray-500" />
                ) : (
                  <ChevronDown size={16} className="text-gray-500" />
                )}
                <h3 className="text-base font-semibold text-gray-100">
                  {series.name}
                </h3>
              </div>
              <div className="flex items-center gap-3">
                {/* Inline progress bar */}
                <div className="hidden sm:flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        seriesPct === 100 ? "bg-green-500" : "bg-indigo-500"
                      }`}
                      style={{ width: `${seriesPct}%` }}
                    />
                  </div>
                </div>
                <span className="text-sm text-gray-400">
                  {series.owned_count}/{series.book_count}
                </span>
              </div>
            </button>

            {!isCollapsed && (
              <div className="mt-2 space-y-1">
                <SeriesBookPlaceholder
                  seriesId={series.id}
                  authorName={author.name}
                />
              </div>
            )}
          </section>
        );
      })}

      {/* Standalone Books */}
      {author.standalone_books.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-200 mb-3">
            Standalone Books
          </h2>
          <div className="space-y-1">
            {author.standalone_books.map((book) => (
              <BookRow key={book.id} book={book} authorName={author.name} />
            ))}
          </div>
        </section>
      )}

      {!isFetching && author.series.length === 0 && author.standalone_books.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <BookOpen size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400">No books found for this author</p>
          <p className="text-sm text-gray-600 mt-1">
            Try refreshing the catalog
          </p>
          <button
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            className="mt-3 inline-flex items-center gap-1.5 px-4 py-2 text-sm text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 rounded-lg transition-colors"
          >
            <RefreshCw size={14} />
            Refresh Catalog
          </button>
        </div>
      )}

      {isFetching && author.series.length === 0 && author.standalone_books.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 skeleton rounded-lg" />
          ))}
        </div>
      )}
    </div>
  );
}

function BookRow({
  book,
  authorName,
  position,
}: {
  book: BookListItem & { owned: boolean };
  authorName: string;
  position?: number;
}) {
  const owned = book.owned;
  return (
    <div
      className={`flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-lg px-4 py-2.5 hover:border-gray-700 transition-colors ${
        !owned ? "opacity-60" : ""
      }`}
    >
      {position != null && (
        <span className="text-xs font-mono text-gray-500 w-6 text-right shrink-0">
          #{position}
        </span>
      )}

      {/* Cover thumbnail */}
      <div className="w-8 h-12 rounded bg-gray-800 overflow-hidden shrink-0 flex items-center justify-center">
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt={book.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <BookOpen size={12} className="text-gray-600" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <Link
          to={`/books/${book.id}`}
          className="text-sm font-medium text-gray-100 truncate hover:text-indigo-400 transition-colors block"
        >
          {book.title}
        </Link>
      </div>

      {/* Owned status */}
      {owned ? (
        <span className="inline-flex items-center gap-1 text-xs text-green-400 shrink-0">
          <Check size={12} />
          In Library
        </span>
      ) : (
        <div className="flex items-center gap-2 shrink-0">
          <span className="inline-flex items-center gap-1 text-xs text-gray-500">
            <X size={12} />
            Missing
          </span>
          <Link
            to={`/search?q=${encodeURIComponent(book.title + " " + authorName)}`}
            className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <Search size={12} />
            Search
          </Link>
        </div>
      )}
    </div>
  );
}

function SeriesBookPlaceholder({
  seriesId,
  authorName,
}: {
  seriesId: string;
  authorName: string;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["series", seriesId],
    queryFn: () => getSeriesDetail(seriesId),
  });

  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-14 skeleton rounded-lg" />
        ))}
      </div>
    );
  }

  if (!data?.books?.length) {
    return (
      <p className="text-sm text-gray-500 px-4 py-2">No books in series</p>
    );
  }

  const sorted = [...data.books].sort((a, b) => a.position - b.position);

  return (
    <div className="space-y-1">
      {sorted.map((book) => (
        <BookRow
          key={book.id}
          book={{ ...book, owned: book.owned ?? false }}
          authorName={authorName}
          position={book.position}
        />
      ))}
    </div>
  );
}
