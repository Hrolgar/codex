import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getBook } from "@/api/client";
import { ArrowLeft, BookOpen, Headphones, Clock, FileText, Search, ExternalLink } from "lucide-react";
import FindReleasesModal from "@/components/FindReleasesModal";

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function BookDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [releasesOpen, setReleasesOpen] = useState(false);

  const { data: book, isLoading, error } = useQuery({
    queryKey: ["book", id],
    queryFn: () => getBook(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-6 w-32 skeleton rounded" />
        <div className="flex flex-col md:flex-row gap-8">
          <div className="w-full md:w-64 aspect-[2/3] skeleton rounded-lg shrink-0" />
          <div className="space-y-4 flex-1">
            <div className="h-8 skeleton rounded w-3/4" />
            <div className="h-4 skeleton rounded w-1/2" />
            <div className="h-20 skeleton rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !book) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <BookOpen size={32} className="text-gray-700 mb-3" />
        <p className="text-gray-400 text-lg">Book not found</p>
        <Link to="/books" className="text-indigo-400 hover:text-indigo-300 text-sm mt-2 inline-block">
          Back to books
        </Link>
      </div>
    );
  }

  const isAudiobook = book.media_type === "audiobook";
  const mediaLabel = book.media_type === 'audiobook' ? 'Audiobook' : book.media_type === 'comic' ? 'Comic' : 'eBook';
  const mediaColor = book.media_type === 'audiobook' ? 'bg-orange-500/15 text-orange-400' : book.media_type === 'comic' ? 'bg-green-500/15 text-green-400' : 'bg-indigo-500/15 text-indigo-400';

  return (
    <div className="space-y-6">
      <Link to="/books" className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors">
        <ArrowLeft size={16} />
        Back to books
      </Link>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Cover */}
        <div className="w-full md:w-64 shrink-0">
          <div className="aspect-[2/3] bg-gray-800 rounded-lg overflow-hidden flex items-center justify-center">
            {book.cover_url ? (
              <img src={book.cover_url} alt={book.title} className="w-full h-full object-cover" />
            ) : (
              <div className="text-gray-600">
                {isAudiobook ? <Headphones size={48} /> : <BookOpen size={48} />}
              </div>
            )}
          </div>
        </div>

        {/* Details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-3">
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-gray-100">{book.title}</h1>
              {book.subtitle && (
                <p className="text-lg text-gray-400 mt-1">{book.subtitle}</p>
              )}
            </div>
            <span
              className={`shrink-0 px-2.5 py-1 rounded text-xs font-medium ${mediaColor}`}
            >
              {mediaLabel}
            </span>
          </div>

          {/* Authors */}
          {book.authors.length > 0 && (
            <p className="text-gray-300 mt-3">
              {book.authors.map((a) => a.name).join(", ")}
            </p>
          )}

          {/* Series */}
          {book.series.length > 0 && (
            <p className="text-sm text-gray-400 mt-1">
              {book.series.map((s) => (
                <Link
                  key={s.id}
                  to={`/series/${s.id}`}
                  className="hover:text-indigo-400 transition-colors"
                >
                  {s.name} #{s.position}
                </Link>
              ))}
            </p>
          )}

          {/* Meta row */}
          <div className="flex flex-wrap gap-4 mt-4 text-sm text-gray-400">
            {book.publish_year && <span>{book.publish_year}</span>}
            {book.language && <span className="uppercase">{book.language}</span>}
            {book.page_count && (
              <span className="flex items-center gap-1">
                <FileText size={14} />
                {book.page_count} pages
              </span>
            )}
            {book.duration_seconds && (
              <span className="flex items-center gap-1">
                <Clock size={14} />
                {formatDuration(book.duration_seconds)}
              </span>
            )}
          </div>

          {/* Description */}
          {book.description && (
            <p className="text-gray-300 mt-6 leading-relaxed">{book.description}</p>
          )}

          {/* Identifiers */}
          <div className="mt-6 space-y-1 text-sm text-gray-500">
            {book.isbn_13 && <p>ISBN-13: {book.isbn_13}</p>}
            {book.isbn_10 && <p>ISBN-10: {book.isbn_10}</p>}
            {book.asin && <p>ASIN: {book.asin}</p>}
          </div>

          {/* Metadata provider link */}
          {(book.hardcover_slug || book.openlibrary_key) && (
            <div className="mt-4">
              <a
                href={
                  book.hardcover_slug
                    ? `https://hardcover.app/books/${book.hardcover_slug}`
                    : `https://openlibrary.org/works/${book.openlibrary_key}`
                }
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-indigo-400 transition-colors"
              >
                <ExternalLink size={14} />
                View on {book.hardcover_slug ? "Hardcover" : "OpenLibrary"}
              </a>
            </div>
          )}

          {/* Library items */}
          {book.library_items.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-300 mb-2">Files</h3>
              <div className="space-y-2">
                {book.library_items.map((item) => (
                  <div key={item.id} className="bg-gray-800/50 rounded px-3 py-2 text-sm">
                    <p className="text-gray-300 truncate">{item.file_path}</p>
                    <div className="flex gap-3 text-xs text-gray-500 mt-1">
                      {item.file_format && <span>{item.file_format.toUpperCase()}</span>}
                      {item.file_size && <span>{(item.file_size / 1048576).toFixed(1)} MB</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {book.library_items.length === 0 && (
            <div className="mt-6 bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
              <p className="text-sm text-gray-400">Not in your library yet</p>
              <Link
                to={`/search?q=${encodeURIComponent(book.title + " " + (book.authors[0]?.name ?? ""))}`}
                className="inline-flex items-center gap-1.5 text-sm text-indigo-400 hover:text-indigo-300 mt-2 transition-colors"
              >
                Search for this book
              </Link>
            </div>
          )}

          {/* Find Releases */}
          <div className="mt-6">
            <button
              onClick={() => setReleasesOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
            >
              <Search size={14} />
              Find Releases
            </button>
          </div>
        </div>
      </div>

      <FindReleasesModal
        open={releasesOpen}
        onClose={() => setReleasesOpen(false)}
        bookTitle={book.title}
        bookAuthor={book.authors[0]?.name}
        mediaType={book.media_type}
      />
    </div>
  );
}
