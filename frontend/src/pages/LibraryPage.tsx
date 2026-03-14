import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBooks } from "@/api/client";
import BookGrid from "@/components/library/BookGrid";
import SearchBar from "@/components/library/SearchBar";

export default function LibraryPage() {
  const [search, setSearch] = useState("");
  const [mediaType, setMediaType] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["books", search, mediaType],
    queryFn: () => getBooks({ search: search || undefined, media_type: mediaType || undefined }),
  });

  const handleSearch = useCallback((q: string) => setSearch(q), []);
  const handleMediaType = useCallback((t: string) => setMediaType(t), []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Library</h2>
        <p className="text-sm text-gray-500 mt-1">
          {data ? `${data.total} books` : "Loading..."}
        </p>
      </div>
      <SearchBar
        onSearch={handleSearch}
        onMediaTypeChange={handleMediaType}
        mediaType={mediaType}
      />
      <BookGrid books={data?.items ?? []} isLoading={isLoading} />
    </div>
  );
}
