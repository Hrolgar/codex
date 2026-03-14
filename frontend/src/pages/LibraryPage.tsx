import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getBooks, seedDemoData } from "@/api/client";
import BookGrid from "@/components/library/BookGrid";
import SearchBar from "@/components/library/SearchBar";

export default function LibraryPage() {
  const queryClient = useQueryClient();
  const seedMutation = useMutation({ mutationFn: seedDemoData, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['books'] }) });
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
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-100">Library</h2>
          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="bg-indigo-500 hover:bg-indigo-600 text-white rounded px-3 py-1.5 text-sm"
          >
            {seedMutation.isPending ? 'Seeding...' : 'Seed Demo Data'}
          </button>
        </div>
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
