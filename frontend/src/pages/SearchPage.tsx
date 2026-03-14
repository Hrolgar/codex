import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBooks } from "@/api/client";
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
      <h2 className="text-2xl font-bold text-gray-100">Search</h2>
      <SearchBar
        onSearch={handleSearch}
        onMediaTypeChange={handleMediaType}
        mediaType={mediaType}
      />
      {search ? (
        <BookGrid books={data?.items ?? []} isLoading={isLoading} />
      ) : (
        <p className="text-center py-16 text-gray-500">
          Type a query to search your library
        </p>
      )}
    </div>
  );
}
