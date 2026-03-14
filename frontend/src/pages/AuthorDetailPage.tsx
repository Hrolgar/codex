import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAuthor } from "@/api/client";
import { ArrowLeft, BookOpen, Library } from "lucide-react";
import BookGrid from "@/components/library/BookGrid";

export default function AuthorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: author, isLoading, error } = useQuery({
    queryKey: ["author", id],
    queryFn: () => getAuthor(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-4 w-24 bg-gray-800 rounded" />
        <div className="h-8 w-48 bg-gray-800 rounded" />
        <div className="h-4 w-16 bg-gray-800 rounded" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-800 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !author) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-400 text-lg">Author not found</p>
        <Link to="/" className="text-indigo-400 hover:text-indigo-300 text-sm mt-2 inline-block">
          Back to authors
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          <ArrowLeft size={16} />
          Back to authors
        </Link>
        <h1 className="text-2xl font-bold text-gray-100 mt-3">{author.name}</h1>
      </div>

      {/* Series */}
      {author.series.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-200 mb-4">Series</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {author.series.map((s) => (
              <Link
                key={s.id}
                to={`/series/${s.id}`}
                className="group bg-gray-900 rounded-lg border border-gray-800 hover:border-indigo-500/50 transition-colors p-4 flex items-center gap-3"
              >
                <div className="w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center shrink-0 group-hover:bg-indigo-500/10 transition-colors">
                  <Library size={18} className="text-gray-400 group-hover:text-indigo-400 transition-colors" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-gray-100 truncate">
                    {s.name}
                  </h3>
                  <p className="text-xs text-gray-500">
                    {s.book_count} book{s.book_count !== 1 ? "s" : ""}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Standalone Books */}
      {author.standalone_books.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-200 mb-4">
            Standalone Books
          </h2>
          <BookGrid books={author.standalone_books} />
        </section>
      )}

      {author.series.length === 0 && author.standalone_books.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <BookOpen size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400">No books found for this author</p>
        </div>
      )}
    </div>
  );
}
