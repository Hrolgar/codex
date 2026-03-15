import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAuthors,
  searchAuthorsExternal,
  addAuthor,
  ExternalAuthor,
} from "@/api/client";
import {
  Search,
  User,
  SearchX,
  AlertCircle,
  Loader2,
  BookOpen,
  Plus,
} from "lucide-react";
import { useSettingsStore } from "@/hooks/useSettingsStore";

export default function AuthorsPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [addingAuthor, setAddingAuthor] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const ss = useSettingsStore();
  const provider = ss.get('search.book_provider', 'openlibrary');
  const providerLabels: Record<string, string> = { openlibrary: 'OpenLibrary', hardcover: 'Hardcover', google: 'Google Books' };
  const providerLabel = providerLabels[provider] || provider;

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 500);
    return () => clearTimeout(timer);
  }, [search]);

  const {
    data: authors,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["authors", debouncedSearch],
    queryFn: () => getAuthors(debouncedSearch || undefined),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.some((a) => a.catalog_status === "fetching")) return 3000;
      return false;
    },
  });

  const { data: externalResults } = useQuery({
    queryKey: ["authors-external", debouncedSearch],
    queryFn: () => searchAuthorsExternal(debouncedSearch),
    enabled: debouncedSearch.length >= 2,
  });

  async function handleAddAuthor(ext: ExternalAuthor) {
    setAddingAuthor(ext.key);
    try {
      await addAuthor(ext.name);
      queryClient.invalidateQueries({ queryKey: ["authors"] });
      queryClient.invalidateQueries({ queryKey: ["authors-external"] });
    } catch {
      // ignore
    } finally {
      setAddingAuthor(null);
    }
  }

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
          placeholder="Search your authors or discover new ones..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>

      {/* Your Authors */}
      {isError ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle size={32} className="text-red-500 mb-3" />
          <p className="text-gray-400">Failed to load authors</p>
          <p className="text-sm text-gray-600 mt-1">Please try again later</p>
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="bg-gray-900 rounded-lg border border-gray-800 animate-pulse p-5"
            >
              <div className="w-16 h-16 bg-gray-800 rounded-lg mx-auto mb-3" />
              <div className="h-3 bg-gray-800 rounded w-3/4 mx-auto mb-2" />
              <div className="h-2 bg-gray-800 rounded w-1/2 mx-auto mb-3" />
              <div className="h-1.5 bg-gray-800 rounded-full w-full" />
            </div>
          ))}
        </div>
      ) : authors && authors.length > 0 ? (
        <>
          {debouncedSearch.length >= 2 && (
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
              Your Authors
            </h3>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {authors.map((author) => {
              const isFetching = author.catalog_status === "fetching";
              const isErrorStatus = author.catalog_status === "error";
              const ownedCount = author.owned_count ?? 0;
              const totalCount = author.book_count;
              const pct =
                totalCount > 0
                  ? Math.round((ownedCount / totalCount) * 100)
                  : 0;

              return (
                <Link
                  key={author.id}
                  to={`/authors/${author.id}`}
                  className={`group bg-gray-900 rounded-lg border transition-colors p-5 text-center ${
                    isFetching
                      ? "border-indigo-500/30"
                      : isErrorStatus
                        ? "border-red-500/30"
                        : "border-gray-800 hover:border-indigo-500/50"
                  }`}
                >
                  <div className="w-16 h-16 rounded-lg mx-auto mb-3 overflow-hidden bg-gray-800 flex items-center justify-center relative">
                    {author.photo_url ? (
                      <img
                        src={author.photo_url}
                        alt={author.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <User
                        size={24}
                        className="text-gray-400 group-hover:text-indigo-400 transition-colors"
                      />
                    )}
                    {isFetching && (
                      <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center">
                        <Loader2
                          size={20}
                          className="text-indigo-400 animate-spin"
                        />
                      </div>
                    )}
                  </div>

                  <h3 className="text-sm font-medium text-gray-100 truncate">
                    {author.name}
                  </h3>

                  {isFetching ? (
                    <p className="text-xs text-indigo-400 mt-1">
                      Loading catalog...
                    </p>
                  ) : isErrorStatus ? (
                    <p className="text-xs text-red-400 mt-1 flex items-center justify-center gap-1">
                      <AlertCircle size={10} />
                      Catalog fetch failed
                    </p>
                  ) : (
                    <p className="text-xs text-gray-500 mt-1">
                      {totalCount} book{totalCount !== 1 ? "s" : ""}
                    </p>
                  )}

                  {isFetching ? (
                    <div className="mt-2 h-1.5 rounded-full bg-gray-800 overflow-hidden">
                      <div className="h-full rounded-full bg-indigo-500/50 animate-pulse w-full" />
                    </div>
                  ) : (
                    <div className="mt-2 h-1.5 rounded-full bg-gray-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-green-500 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  )}

                  {author.monitored && (
                    <span className="inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium bg-green-500/15 text-green-400">
                      Monitored
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <SearchX size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400">No authors found</p>
          <p className="text-sm text-gray-600 mt-1">
            {search
              ? "Try adjusting your search"
              : "Search for an author to start tracking their catalog"}
          </p>
        </div>
      )}

      {/* Discover Authors */}
      {debouncedSearch.length >= 2 &&
        externalResults &&
        externalResults.length > 0 && (
          <div className="border border-gray-800 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <BookOpen size={14} className="text-gray-500" />
              <h3 className="text-sm font-medium text-gray-400">
                Discover Authors
              </h3>
              <span className="text-xs text-gray-600">From {providerLabel}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {externalResults.map((ext) => (
                <div
                  key={ext.key}
                  className="flex items-center justify-between gap-3 bg-gray-900/50 rounded-lg border border-gray-800/50 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-200 truncate">
                      {ext.name}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {ext.work_count} work{ext.work_count !== 1 ? "s" : ""}
                      {ext.top_work ? ` · ${ext.top_work}` : ""}
                    </p>
                  </div>
                  <button
                    onClick={() => handleAddAuthor(ext)}
                    disabled={addingAuthor === ext.key}
                    className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-md transition-colors"
                  >
                    {addingAuthor === ext.key ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Plus size={12} />
                    )}
                    Add
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
    </div>
  );
}
