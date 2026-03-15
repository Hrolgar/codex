import { useState, useMemo } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAuthor, refreshAuthor, deleteAuthor, getSeriesDetail } from "@/api/client";
import type { AuthorMediaGroup } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import AuthorBookRow from "@/components/AuthorBookRow";
import FindReleasesModal from "@/components/FindReleasesModal";
import {
  ArrowLeft,
  BookOpen,
  RefreshCw,
  Trash2,
  User,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
} from "lucide-react";

const MEDIA_LABELS: Record<string, string> = {
  ebook: "eBooks",
  audiobook: "Audiobooks",
  comic: "Comics",
};

export default function AuthorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [findRelease, setFindRelease] = useState<{ title: string; author: string; mediaType: string } | null>(null);
  const [bioExpanded, setBioExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("");

  const { data: author, isLoading, error } = useQuery({
    queryKey: ["author", id],
    queryFn: () => getAuthor(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      if (query.state.data?.catalog_status === "fetching") return 3000;
      return false;
    },
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshAuthor(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["author", id] });
      addToast("Refreshing catalog...", "info");
    },
    onError: () => addToast("Failed to refresh catalog", "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: (removeBooks: boolean) => deleteAuthor(id!, removeBooks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authors"] });
      addToast("Author deleted");
      navigate("/");
    },
  });

  const groups: AuthorMediaGroup[] = useMemo(() => {
    if (!author) return [];
    if (author.media_groups?.length) return author.media_groups;
    const map: Record<string, any[]> = {};
    for (const b of author.standalone_books || []) {
      const mt = b.media_type || "ebook";
      (map[mt] ??= []).push(b);
    }
    return Object.entries(map).map(([mt, books]) => ({
      media_type: mt,
      books,
      total: books.length,
      owned: books.filter((b: any) => b.owned).length,
      missing: books.filter((b: any) => !b.owned && b.monitored !== false).length,
      not_monitored: books.filter((b: any) => b.monitored === false).length,
    }));
  }, [author]);

  const currentTab = activeTab || groups[0]?.media_type || "ebook";
  const activeGroup = groups.find((g) => g.media_type === currentTab);

  const totalBooks = groups.reduce((s, g) => s + g.total, 0);
  const ownedBooks = groups.reduce((s, g) => s + g.owned, 0);
  const missingBooks = groups.reduce((s, g) => s + g.missing, 0);
  const notMonitored = groups.reduce((s, g) => s + g.not_monitored, 0);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-4 w-24 skeleton rounded" />
        <div className="flex gap-6">
          <div className="w-32 h-32 skeleton rounded-lg shrink-0" />
          <div className="space-y-3 flex-1">
            <div className="h-8 w-48 skeleton rounded" />
            <div className="h-4 w-full skeleton rounded" />
            <div className="h-4 w-3/4 skeleton rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !author) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <User size={32} className="text-gray-700 mb-3" />
        <p className="text-gray-400 text-lg">Author not found</p>
        <Link to="/" className="text-indigo-400 hover:text-indigo-300 text-sm mt-2 inline-block">Back to authors</Link>
      </div>
    );
  }

  const isFetching = author.catalog_status === "fetching";
  const isCatalogError = author.catalog_status === "error";
  const handleSearch = (title: string, auth: string, mediaType: string) => setFindRelease({ title, author: auth, mediaType });

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors">
        <ArrowLeft size={16} /> Back to authors
      </Link>

      {/* Header */}
      <div className="flex gap-6">
        <div className="w-32 h-32 rounded-lg bg-gray-800 overflow-hidden shrink-0 flex items-center justify-center">
          {author.photo_url ? (
            <img src={author.photo_url} alt={author.name} className="w-full h-full object-cover" />
          ) : (
            <User size={48} className="text-gray-600" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <h1 className="text-2xl font-bold text-gray-100">{author.name}</h1>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => addToast(author.monitored ? "Monitoring paused" : "Monitoring all books", "info")}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  author.monitored ? "text-green-400 bg-green-500/10 hover:bg-green-500/20" : "text-gray-400 bg-gray-800 hover:bg-gray-700"
                }`}
              >
                {author.monitored ? <Eye size={14} /> : <EyeOff size={14} />}
                {author.monitored ? "Monitored" : "Monitor"}
              </button>
              <button
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw size={14} className={refreshMutation.isPending ? "animate-spin" : ""} />
                Refresh
              </button>
              {showDeleteConfirm ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-red-400">Remove books too?</span>
                  <button onClick={() => deleteMutation.mutate(true)} disabled={deleteMutation.isPending} className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors">
                    {deleteMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : "Remove Books"}
                  </button>
                  <button onClick={() => deleteMutation.mutate(false)} disabled={deleteMutation.isPending} className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                    Keep Books
                  </button>
                  <button onClick={() => setShowDeleteConfirm(false)} className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-300 transition-colors">Cancel</button>
                </div>
              ) : (
                <button onClick={() => setShowDeleteConfirm(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                  <Trash2 size={14} /> Delete
                </button>
              )}
            </div>
          </div>

          {author.bio && (
            <div className="mt-3 bg-gray-900/50 rounded-lg p-3">
              <p className={`text-sm text-gray-400 leading-relaxed ${!bioExpanded ? "line-clamp-3" : ""}`}>{author.bio}</p>
              {author.bio.length > 300 && (
                <button onClick={() => setBioExpanded(!bioExpanded)} className="text-xs text-indigo-400 hover:text-indigo-300 mt-1.5 transition-colors">
                  {bioExpanded ? "Show less" : "Show more"}
                </button>
              )}
            </div>
          )}

          {/* Stats bar */}
          <div className="flex items-center gap-3 mt-3 text-sm">
            <span className="text-gray-300"><span className="font-semibold text-gray-100">{totalBooks}</span> total</span>
            <span className="text-gray-600">&middot;</span>
            <span className="text-green-400"><span className="font-semibold">{ownedBooks}</span> owned</span>
            <span className="text-gray-600">&middot;</span>
            <span className="text-yellow-400"><span className="font-semibold">{missingBooks}</span> missing</span>
            {notMonitored > 0 && (
              <>
                <span className="text-gray-600">&middot;</span>
                <span className="text-gray-500"><span className="font-semibold">{notMonitored}</span> not monitored</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Catalog status banners */}
      {isFetching && (
        <div className="flex items-center gap-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg px-4 py-3">
          <Loader2 size={18} className="text-indigo-400 animate-spin shrink-0" />
          <div>
            <p className="text-sm font-medium text-indigo-400">Fetching bibliography...</p>
            <p className="text-xs text-indigo-400/70 mt-0.5">This may take a minute for prolific authors.</p>
          </div>
        </div>
      )}

      {isCatalogError && (
        <div className="flex items-center justify-between bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          <div className="flex items-center gap-3">
            <AlertCircle size={18} className="text-red-400 shrink-0" />
            <p className="text-sm text-red-400">Failed to fetch catalog.</p>
          </div>
          <button onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors">
            <RefreshCw size={14} className={refreshMutation.isPending ? "animate-spin" : ""} /> Retry
          </button>
        </div>
      )}

      {/* Media type tabs */}
      {groups.length > 0 && (
        <div className="flex gap-1">
          {groups.map((g) => (
            <button
              key={g.media_type}
              onClick={() => setActiveTab(g.media_type)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                currentTab === g.media_type
                  ? "bg-indigo-500/20 text-indigo-400"
                  : "text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700"
              }`}
            >
              {MEDIA_LABELS[g.media_type] || g.media_type} ({g.total})
            </button>
          ))}
        </div>
      )}

      {/* Book list for active tab */}
      {activeGroup && activeGroup.books.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          {activeGroup.books.map((book: any) => (
            <AuthorBookRow key={book.id} book={book} authorName={author.name} onSearch={handleSearch} />
          ))}
        </div>
      )}

      {/* Series in the current tab */}
      {author.series.map((series) => (
        <SeriesSection
          key={series.id}
          seriesId={series.id}
          seriesName={series.name}
          ownedCount={series.owned_count}
          bookCount={series.book_count}
          authorName={author.name}
          mediaType={currentTab}
          onSearch={handleSearch}
        />
      ))}

      {/* Empty state */}
      {!isFetching && groups.length === 0 && author.series.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <BookOpen size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400">No books found for this author</p>
          <button onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending} className="mt-3 inline-flex items-center gap-1.5 px-4 py-2 text-sm text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 rounded-lg transition-colors">
            <RefreshCw size={14} /> Refresh Catalog
          </button>
        </div>
      )}

      {isFetching && groups.length === 0 && author.series.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 skeleton rounded-lg" />
          ))}
        </div>
      )}

      {findRelease && (
        <FindReleasesModal
          open={!!findRelease}
          onClose={() => setFindRelease(null)}
          bookTitle={findRelease.title}
          bookAuthor={findRelease.author}
          mediaType={findRelease.mediaType}
        />
      )}
    </div>
  );
}

function SeriesSection({
  seriesId,
  seriesName,
  ownedCount,
  bookCount,
  authorName,
  mediaType,
  onSearch,
}: {
  seriesId: string;
  seriesName: string;
  ownedCount: number;
  bookCount: number;
  authorName: string;
  mediaType: string;
  onSearch: (title: string, author: string, mediaType: string) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["series", seriesId],
    queryFn: () => getSeriesDetail(seriesId),
  });

  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-14 skeleton rounded-lg" />
        ))}
      </div>
    );
  }

  const books = data?.books ? [...data.books].sort((a, b) => a.position - b.position) : [];
  if (books.length === 0) return null;

  const pct = bookCount > 0 ? Math.round((ownedCount / bookCount) * 100) : 0;

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-300">{seriesName}</h3>
        <div className="flex items-center gap-2">
          <div className="w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${pct === 100 ? "bg-green-500" : "bg-indigo-500"}`} style={{ width: `${pct}%` }} />
          </div>
          <span className="text-xs text-gray-500">{ownedCount}/{bookCount}</span>
        </div>
      </div>
      <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
        {books.map((book) => (
          <AuthorBookRow
            key={book.id}
            book={{ ...book, owned: book.owned ?? false, monitored: true, media_type: book.media_type || mediaType }}
            authorName={authorName}
            onSearch={onSearch}
          />
        ))}
      </div>
    </section>
  );
}
