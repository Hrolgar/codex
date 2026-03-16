import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getSeries } from "@/api/client";
import { Search, BookOpen, AlertCircle, SearchX } from "lucide-react";

export default function SeriesPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 500);
    return () => clearTimeout(timer);
  }, [search]);

  const {
    data: seriesList,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["series", debouncedSearch],
    queryFn: () => getSeries(debouncedSearch || undefined),
  });

  const sorted = seriesList
    ? [...seriesList].sort((a, b) => a.name.localeCompare(b.name))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Series</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {seriesList
            ? `${seriesList.length} series`
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
          placeholder="Search series..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>

      {isError ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle size={32} className="text-red-500 mb-3" />
          <p className="text-gray-400">Failed to load series</p>
          <p className="text-sm text-gray-600 mt-1">Please try again later</p>
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="bg-gray-900 rounded-lg border border-gray-800 animate-pulse p-4 flex items-center gap-4"
            >
              <div className="w-10 h-10 bg-gray-800 rounded-lg" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 bg-gray-800 rounded w-1/3" />
                <div className="h-3 bg-gray-800 rounded w-1/5" />
              </div>
              <div className="h-3 bg-gray-800 rounded w-16" />
            </div>
          ))}
        </div>
      ) : sorted.length > 0 ? (
        <div className="space-y-2">
          {sorted.map((series) => (
            <Link
              key={series.id}
              to={`/series/${series.id}`}
              className="group flex items-center gap-4 bg-gray-900 rounded-lg border border-gray-800 hover:border-indigo-500/50 transition-colors p-4"
            >
              <div className="w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center shrink-0">
                <BookOpen
                  size={18}
                  className="text-gray-500 group-hover:text-indigo-400 transition-colors"
                />
              </div>

              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-medium text-gray-100 truncate">
                  {series.name}
                </h3>
                <p className="text-xs text-gray-500 truncate mt-0.5">
                  {series.author_names || "Unknown author"}
                </p>
              </div>

              <span className="text-xs text-gray-500 shrink-0">
                {series.book_count} book{series.book_count !== 1 ? "s" : ""}
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <SearchX size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400">No series found</p>
          <p className="text-sm text-gray-600 mt-1">
            {search
              ? "Try adjusting your search"
              : "Series will appear here when authors with series are added"}
          </p>
        </div>
      )}
    </div>
  );
}
