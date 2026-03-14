import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBooks } from "@/api/client";
import { Search } from "lucide-react";
import BookGrid from "@/components/library/BookGrid";
import SearchBar from "@/components/library/SearchBar";

export default function SearchPage() {
  const [search, setSearch] = useState("");
  const [mediaType, setMediaType] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["search", search, mediaType],
    queryFn: () => getBooks({ search, media_type: mediaType || undefined }),
    enabled: search.length > 0,
  });

  const handleSearch = useCallback((q: string) => setSearch(q), []);
  const handleMediaType = useCallback((t: string) => setMediaType(t), []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Search</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Search across your library
        </p>
      </div>

      <SearchBar
        onSearch={handleSearch}
        onMediaTypeChange={handleMediaType}
        mediaType={mediaType}
      />

      {search ? (
        <>
          {data && !isLoading && (
            <p className="text-sm text-gray-500">
              {data.total} result{data.total !== 1 ? "s" : ""} for "{search}"
            </p>
          )}
          <BookGrid books={data?.items ?? []} isLoading={isLoading} />
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-14 h-14 rounded-xl bg-gray-800/50 flex items-center justify-center mb-4">
            <Search size={24} className="text-gray-600" />
          </div>
          <p className="text-gray-500">
            Start typing to search your library
          </p>
        </div>
      )}
    </div>
  );
}
