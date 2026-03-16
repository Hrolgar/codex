import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getSeriesDetail } from "@/api/client";
import { ArrowLeft, BookOpen, Headphones, Search, Check, X } from "lucide-react";

export default function SeriesDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: series, isLoading, error } = useQuery({
    queryKey: ["series", id],
    queryFn: () => getSeriesDetail(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div>
          <div className="h-4 w-24 bg-gray-800 rounded mb-3" />
          <div className="h-8 w-64 bg-gray-800 rounded mb-2" />
          <div className="h-4 w-32 bg-gray-800 rounded" />
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="h-4 w-32 bg-gray-800 rounded" />
            <div className="h-4 w-12 bg-gray-800 rounded" />
          </div>
          <div className="h-2.5 bg-gray-800 rounded-full" />
        </div>
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 bg-gray-900 rounded-lg border border-gray-800 p-3">
              <div className="w-10 h-5 bg-gray-800 rounded" />
              <div className="w-12 h-[4.5rem] bg-gray-800 rounded" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 bg-gray-800 rounded w-2/5" />
                <div className="h-3 bg-gray-800 rounded w-1/4" />
              </div>
              <div className="h-4 w-16 bg-gray-800 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !series) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <BookOpen size={32} className="text-gray-700 mb-3" />
        <p className="text-gray-400 text-lg">Series not found</p>
        <Link to="/" className="text-indigo-400 hover:text-indigo-300 text-sm mt-2 inline-block">
          Back to authors
        </Link>
      </div>
    );
  }

  const sortedBooks = [...series.books].sort((a, b) => {
    if (a.position === null && b.position === null) return 0;
    if (a.position === null) return 1;
    if (b.position === null) return -1;
    return a.position - b.position;
  });

  const ownedCount = sortedBooks.filter((b) => b.owned).length;
  const totalCount = sortedBooks.length;
  const pct = totalCount > 0 ? Math.round((ownedCount / totalCount) * 100) : 0;
  const missingBooks = sortedBooks.filter((b) => !b.owned);

  const backTo = "/series";
  const backLabel = "Series";

  const authorName = series.authors.map((a) => a.name).join(", ");

  return (
    <div className="space-y-6">
      <div>
        <Link
          to={backTo}
          className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          <ArrowLeft size={16} />
          {backLabel}
        </Link>
        <h1 className="text-2xl font-bold text-gray-100 mt-3">{series.name}</h1>
        {series.authors.length > 0 && (
          <p className="text-sm text-gray-400 mt-1">by {authorName}</p>
        )}
      </div>

      {/* Progress bar */}
      {totalCount > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-200">
              Owned {ownedCount}/{totalCount} books
            </span>
            <span className="text-sm text-gray-400">{pct}%</span>
          </div>
          <div className="h-2.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                pct === 100 ? "bg-green-500" : "bg-indigo-500"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
          {missingBooks.length > 0 && (
            <div className="mt-3 flex justify-end">
              <Link
                to={`/search?q=${encodeURIComponent(series.name + " " + authorName)}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 rounded-lg transition-colors"
              >
                <Search size={14} />
                Search Missing ({missingBooks.length})
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Books list */}
      {sortedBooks.length > 0 ? (
        <div className="space-y-2">
          {sortedBooks.map((book) => {
            const isAudiobook = book.media_type === "audiobook";
            const owned = book.owned ?? false;
            return (
              <Link
                key={book.id}
                to={`/books/${book.id}`}
                className={`group flex items-center gap-4 bg-gray-900 rounded-lg border transition-colors p-3 ${
                  owned
                    ? "border-gray-800 hover:border-indigo-500/50"
                    : "border-gray-800/60 hover:border-gray-700 opacity-70"
                }`}
              >
                {/* Position */}
                <div className="w-10 text-center shrink-0">
                  {book.position !== null ? (
                    <span className="text-sm font-mono font-bold text-gray-500">
                      #{book.position}
                    </span>
                  ) : (
                    <span className="text-sm text-gray-600">—</span>
                  )}
                </div>

                {/* Cover thumbnail */}
                <div className="w-12 h-[4.5rem] bg-gray-800 rounded overflow-hidden flex items-center justify-center shrink-0">
                  {book.cover_url ? (
                    <img
                      src={book.cover_url}
                      alt={book.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="text-gray-600">
                      {isAudiobook ? <Headphones size={16} /> : <BookOpen size={16} />}
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-medium text-gray-100 truncate">
                    {book.title}
                  </h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        isAudiobook
                          ? "bg-purple-500/20 text-purple-400"
                          : "bg-indigo-500/20 text-indigo-400"
                      }`}
                    >
                      {isAudiobook ? "Audio" : "eBook"}
                    </span>
                    {book.publish_year && (
                      <span className="text-xs text-gray-500">
                        {book.publish_year}
                      </span>
                    )}
                  </div>
                </div>

                {/* Owned status */}
                <div className="shrink-0">
                  {owned ? (
                    <span className="inline-flex items-center gap-1 text-xs text-green-400">
                      <Check size={14} />
                      Owned
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                      <X size={14} />
                      Missing
                    </span>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <BookOpen size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400">No books in this series</p>
          <Link
            to={`/search?q=${encodeURIComponent(series.name)}`}
            className="mt-3 inline-flex items-center gap-1.5 text-sm text-indigo-400 hover:text-indigo-300"
          >
            <Search size={14} />
            Search for books
          </Link>
        </div>
      )}
    </div>
  );
}
