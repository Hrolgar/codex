import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getSeriesDetail } from "@/api/client";
import { ArrowLeft, BookOpen, Headphones } from "lucide-react";

export default function SeriesDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: series, isLoading, error } = useQuery({
    queryKey: ["series", id],
    queryFn: () => getSeriesDetail(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-4 w-24 bg-gray-800 rounded" />
        <div className="h-8 w-48 bg-gray-800 rounded" />
        <div className="h-4 w-32 bg-gray-800 rounded" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 bg-gray-800 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !series) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-400 text-lg">Series not found</p>
        <Link to="/" className="text-indigo-400 hover:text-indigo-300 text-sm mt-2 inline-block">
          Back to authors
        </Link>
      </div>
    );
  }

  // Sort books by position, nulls last
  const sortedBooks = [...series.books].sort((a, b) => {
    if (a.position === null && b.position === null) return 0;
    if (a.position === null) return 1;
    if (b.position === null) return -1;
    return a.position - b.position;
  });

  // Back link: go to first author if available, otherwise authors list
  const backTo = series.authors.length > 0
    ? `/authors/${series.authors[0].id}`
    : "/";
  const backLabel = series.authors.length > 0
    ? series.authors[0].name
    : "Authors";

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
          <p className="text-sm text-gray-400 mt-1">
            by {series.authors.map((a) => a.name).join(", ")}
          </p>
        )}
      </div>

      {/* Books list */}
      {sortedBooks.length > 0 ? (
        <div className="space-y-3">
          {sortedBooks.map((book) => {
            const isAudiobook = book.media_type === "audiobook";
            return (
              <Link
                key={book.id}
                to={`/books/${book.id}`}
                className="group flex items-center gap-4 bg-gray-900 rounded-lg border border-gray-800 hover:border-indigo-500/50 transition-colors p-3"
              >
                {/* Position */}
                <div className="w-8 text-center shrink-0">
                  {book.position !== null ? (
                    <span className="text-lg font-bold text-gray-500">
                      {book.position}
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
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <BookOpen size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400">No books in this series</p>
        </div>
      )}
    </div>
  );
}
