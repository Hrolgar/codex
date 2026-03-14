import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAuthors } from "@/api/client";
import { Search, User, SearchX } from "lucide-react";

export default function AuthorsPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data: authors, isLoading } = useQuery({
    queryKey: ["authors", debouncedSearch],
    queryFn: () => getAuthors(debouncedSearch || undefined),
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Authors</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {authors
            ? `${authors.length} author${authors.length !== 1 ? "s" : ""}`
            : "Loading..."}
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
        />
        <input
          type="text"
          placeholder="Search authors..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="bg-gray-900 rounded-lg border border-gray-800 animate-pulse p-5"
            >
              <div className="w-12 h-12 bg-gray-800 rounded-full mx-auto mb-3" />
              <div className="h-3 bg-gray-800 rounded w-3/4 mx-auto mb-2" />
              <div className="h-2 bg-gray-800 rounded w-1/2 mx-auto" />
            </div>
          ))}
        </div>
      ) : authors && authors.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {authors.map((author) => (
            <Link
              key={author.id}
              to={`/authors/${author.id}`}
              className="group bg-gray-900 rounded-lg border border-gray-800 hover:border-indigo-500/50 transition-colors p-5 text-center"
            >
              <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center mx-auto mb-3 group-hover:bg-indigo-500/10 transition-colors">
                <User size={20} className="text-gray-400 group-hover:text-indigo-400 transition-colors" />
              </div>
              <h3 className="text-sm font-medium text-gray-100 truncate">
                {author.name}
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                {author.book_count} book{author.book_count !== 1 ? "s" : ""}
              </p>
            </Link>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <SearchX size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400">No authors found</p>
          <p className="text-sm text-gray-600 mt-1">
            Try adjusting your search
          </p>
        </div>
      )}
    </div>
  );
}
