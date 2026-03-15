import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { searchExternal, createDownload, addToWishlist } from "@/api/client";
import type { SearchResult } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import {
  Search,
  Download,
  Check,
  AlertCircle,
  Loader2,
  BookOpen,
  Star,
} from "lucide-react";

export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";
  const [search, setSearch] = useState(initialQuery);
  const [debouncedSearch, setDebouncedSearch] = useState(initialQuery);
  const [mediaType, setMediaType] = useState("");
  const [downloadingUrls, setDownloadingUrls] = useState<Set<string>>(
    new Set()
  );
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  // Sync from URL query param when it changes (e.g. navigating from author page)
  const prevQRef = useRef(initialQuery);
  useEffect(() => {
    const q = searchParams.get("q") ?? "";
    if (q !== prevQRef.current) {
      prevQRef.current = q;
      setSearch(q);
      setDebouncedSearch(q);
    }
  }, [searchParams]);

  const wishlistMutation = useMutation({
    mutationFn: addToWishlist,
    onSuccess: () => {
      addToast("Added to wishlist");
    },
    onError: () => {
      addToast("Failed to add to wishlist", "error");
    },
  });

  const handleWishlist = (result: SearchResult) => {
    wishlistMutation.mutate({
      search_title: result.title,
      search_author: result.author ?? "",
    });
  };

  // Debounce via ref to avoid re-renders on every keystroke
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const onSearchChange = useCallback(
    (value: string) => {
      setSearch(value);
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setDebouncedSearch(value), 300);
    },
    []
  );

  const { data, isLoading, isError } = useQuery({
    queryKey: ["external-search", debouncedSearch, mediaType],
    queryFn: () =>
      searchExternal(debouncedSearch, mediaType || undefined),
    enabled: debouncedSearch.length >= 3,
  });

  const downloadMutation = useMutation({
    mutationFn: createDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["downloads"] });
    },
  });

  const handleDownload = (result: SearchResult) => {
    if (!result.source) return;
    setDownloadingUrls((prev) => new Set(prev).add(result.source!));
    downloadMutation.mutate(
      {
        source_url: result.source!,
        source_type: result.source!,
        book_id: result.book_id ?? undefined,
      },
      {
        onSettled: () => {
          setDownloadingUrls((prev) => {
            const next = new Set(prev);
            next.delete(result.source!);
            return next;
          });
        },
      }
    );
  };

  const mediaTypes = [
    { value: "", label: "All" },
    { value: "ebook", label: "eBooks" },
    { value: "audiobook", label: "Audiobooks" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Search</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Search external sources for books
        </p>
      </div>

      {/* Search bar + media type filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
          />
          <input
            type="text"
            placeholder="Search for books (min 3 characters)..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
        <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
          {mediaTypes.map((t) => (
            <button
              key={t.value}
              onClick={() => setMediaType(t.value)}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                mediaType === t.value
                  ? "bg-indigo-500 text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {debouncedSearch.length < 3 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-14 h-14 rounded-xl bg-gray-800/50 flex items-center justify-center mb-4">
            <Search size={24} className="text-gray-600" />
          </div>
          <p className="text-gray-500">
            Start typing to search external sources
          </p>
        </div>
      ) : isLoading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 size={24} className="text-indigo-400 animate-spin mb-3" />
          <p className="text-sm text-gray-500">Searching...</p>
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle size={24} className="text-red-400 mb-3" />
          <p className="text-sm text-red-400">
            Search failed. Please try again.
          </p>
        </div>
      ) : data && data.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Search size={24} className="text-gray-600 mb-3" />
          <p className="text-gray-500">
            No results found for "{debouncedSearch}"
          </p>
        </div>
      ) : (
        <>
          <p className="text-sm text-gray-500">
            {data?.length} result{data?.length !== 1 ? "s" : ""} for "
            {debouncedSearch}"
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {data?.map((result, idx) => (
              <SearchResultCard
                key={`${result.title}-${result.source}-${idx}`}
                result={result}
                onDownload={handleDownload}
                onWishlist={handleWishlist}
                isDownloading={downloadingUrls.has(result.source ?? "")}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function SearchResultCard({
  result,
  onDownload,
  onWishlist,
  isDownloading,
}: {
  result: SearchResult;
  onDownload: (r: SearchResult) => void;
  onWishlist: (r: SearchResult) => void;
  isDownloading: boolean;
}) {
  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden border border-gray-800 flex flex-col">
      {/* Cover */}
      <div className="aspect-[2/3] bg-gray-800 flex items-center justify-center relative">
        {result.cover_url ? (
          <img
            src={result.cover_url}
            alt={result.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-600">
            <BookOpen size={32} />
          </div>
        )}
        {/* Badges */}
        <div className="absolute top-2 right-2 flex flex-col gap-1">
          {result.source && (
            <span className="rounded-full px-2 py-0.5 text-xs bg-gray-700 text-gray-300">
              {result.source}
            </span>
          )}
          {result.owned && (
            <span className="rounded-full px-2 py-0.5 text-xs bg-green-500/20 text-green-400 flex items-center gap-1">
              <Check size={10} />
              Owned
              {result.match_confidence < 1 && (
                <span className="opacity-70">
                  {Math.round(result.match_confidence * 100)}%
                </span>
              )}
            </span>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="p-3 flex-1 flex flex-col">
        <h3 className="text-sm font-medium text-gray-100 truncate">
          {result.title}
        </h3>
        <p className="text-xs text-gray-400 truncate mt-1">
          {result.author ?? "Unknown author"}
        </p>

        <div className="mt-auto pt-3 flex gap-2">
          <button
            onClick={() => onDownload(result)}
            disabled={isDownloading || !result.source}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDownloading ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Download size={14} />
                Download
              </>
            )}
          </button>
          {!result.owned && (
            <button
              onClick={() => onWishlist(result)}
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30"
              title="Add to Wishlist"
            >
              <Star size={14} />
              Wishlist
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
