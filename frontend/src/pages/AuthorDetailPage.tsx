import { useState, useMemo } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAuthor, refreshAuthor, deleteAuthor } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import FindReleasesModal from "@/components/FindReleasesModal";
import AuthorBookRow from "@/components/AuthorBookRow";
import {
  ArrowLeft,
  RefreshCw,
  Trash2,
  User,
  Check,
  X,
  Loader2,
  AlertCircle,
} from "lucide-react";

interface MediaGroup {
  media_type: string;
  books: any[];
  total: number;
  owned: number;
  missing: number;
  not_monitored: number;
}

const TAB_LABELS: Record<string, string> = {
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
  const [activeTab, setActiveTab] = useState<string | null>(null);

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
  });

  const deleteMutation = useMutation({
    mutationFn: (removeBooks: boolean) => deleteAuthor(id!, removeBooks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authors"] });
      addToast("Author deleted");
      navigate("/");
    },
  });

  // Build media groups from API response or client-side grouping
  const groups: MediaGroup[] = useMemo(() => {
    if (!author) return [];
    if (author.media_groups?.length) return author.media_groups;

    // Fallback: group all books (series + standalone) by media_type
    const allBooks = [
      ...(author.standalone_books || []),
      ...(author.series?.flatMap((s: any) => s.books || []) || []),
    ];
    const map: Record<string, any[]> = {};
    for (const b of allBooks) {
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

  // Set initial tab
  const currentTab = activeTab || groups[0]?.media_type || "ebook";
  const activeGroup = groups.find((g) => g.media_type === currentTab);

  // Total stats across all groups
  const totalBooks = groups.reduce((s, g) => s + g.total, 0);
  const ownedBooks = groups.reduce((s, g) => s + g.owned, 0);
  const missingBooks = groups.reduce((s, g) => s + g.missing, 0);
  const notMonitored = groups.reduce((s, g) => s + g.not_monitored, 0);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-4 w-24 skeleton rounded" />
        <div className="flex gap-6">
          <div className="w-24 h-24 skeleton rounded-lg shrink-0" />
          <div className="space-y-3 flex-1">
            <div className="h-8 w-48 skeleton rounded" />
            <div className="h-4 w-full skeleton rounded" />
            <div className="h-4 w-3/4 skeleton rounded" />
          </div>
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-14 skeleton rounded-lg" />
        ))}
      </div>
    );
  }

  if (error || !author) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <User size={32} className="text-gray-700 mb-3" />
        <p className="text-gray-400 text-lg">Author not found</p>
        <Link to="/" className="text-indigo-400 hover:text-indigo-300 text-sm mt-2">
          Back to authors
        </Link>
      </div>
    );
  }

  const isFetching = author.catalog_status === "fetching";

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors">
        <ArrowLeft size={14} /> Back to authors
      </Link>

      {/* Header */}
      <div className="flex gap-6">
        {/* Photo */}
        <div className="w-24 h-24 rounded-lg overflow-hidden bg-gray-800 shrink-0 flex items-center justify-center">
          {author.photo_url ? (
            <img src={author.photo_url} alt={author.name} className="w-full h-full object-cover" />
          ) : (
            <User size={32} className="text-gray-600" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-100">{author.name}</h1>
              <p className="text-sm text-gray-500 mt-0.5">{totalBooks} books total · {ownedBooks} owned</p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 shrink-0">
              {author.monitored && (
                <span className="px-2.5 py-1 rounded text-xs font-medium bg-green-500/15 text-green-400 flex items-center gap-1">
                  <Check size={12} /> Monitored
                </span>
              )}
              <button
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending || isFetching}
                className="p-2 text-gray-400 hover:text-gray-200 transition-colors disabled:opacity-50"
                title="Refresh catalog"
              >
                <RefreshCw size={16} className={isFetching ? "animate-spin" : ""} />
              </button>
              {!showDeleteConfirm ? (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                  title="Delete author"
                >
                  <Trash2 size={16} />
                </button>
              ) : (
                <div className="flex items-center gap-1 bg-red-500/10 border border-red-500/30 rounded-lg px-2 py-1">
                  <span className="text-xs text-red-400 mr-1">Delete?</span>
                  <button onClick={() => deleteMutation.mutate(true)} className="p-1 text-red-400 hover:text-red-300" title="Delete with books">
                    <Trash2 size={14} />
                  </button>
                  <button onClick={() => setShowDeleteConfirm(false)} className="p-1 text-gray-400 hover:text-gray-200">
                    <X size={14} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Bio */}
          {author.bio && (
            <div className="mt-3">
              <p className={`text-sm text-gray-400 leading-relaxed ${bioExpanded ? "" : "line-clamp-2"}`}>
                {author.bio}
              </p>
              {author.bio.length > 200 && (
                <button onClick={() => setBioExpanded(!bioExpanded)} className="text-xs text-indigo-400 hover:text-indigo-300 mt-1">
                  {bioExpanded ? "Show less" : "Show more"}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Fetching banner */}
      {isFetching && (
        <div className="flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-4 py-2">
          <Loader2 size={14} className="text-indigo-400 animate-spin" />
          <span className="text-sm text-indigo-300">Loading catalog from OpenLibrary...</span>
        </div>
      )}

      {author.catalog_status === "error" && (
        <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2">
          <AlertCircle size={14} className="text-red-400" />
          <span className="text-sm text-red-300">Catalog fetch failed. Try refreshing.</span>
        </div>
      )}

      {/* Stats bar */}
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-300 font-medium">{totalBooks} total</span>
        <span className="text-green-400">{ownedBooks} owned</span>
        <span className="text-yellow-400">{missingBooks} missing</span>
        {notMonitored > 0 && <span className="text-gray-500">{notMonitored} not monitored</span>}
      </div>

      {/* Tabs */}
      {groups.length > 0 && (
        <div className="border-b border-gray-800">
          <div className="flex gap-0">
            {groups.map((g) => (
              <button
                key={g.media_type}
                onClick={() => setActiveTab(g.media_type)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  currentTab === g.media_type
                    ? "border-indigo-500 text-gray-100"
                    : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
              >
                {TAB_LABELS[g.media_type] || g.media_type} ({g.total})
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Book list for active tab */}
      {activeGroup && activeGroup.books.length > 0 ? (
        <div className="border border-gray-800 rounded-lg overflow-hidden">
          {activeGroup.books.map((book: any) => (
            <AuthorBookRow
              key={book.id}
              book={book}
              authorName={author.name}
              onSearch={(title, auth, mediaType) => setFindRelease({ title, author: auth, mediaType })}
            />
          ))}
        </div>
      ) : groups.length === 0 && !isFetching ? (
        <div className="text-center py-12 text-gray-500">
          <p>No books found for this author.</p>
          <p className="text-sm mt-1">Try refreshing the catalog.</p>
        </div>
      ) : null}

      {/* Find Releases Modal */}
      {findRelease && (
        <FindReleasesModal
          open={true}
          onClose={() => setFindRelease(null)}
          bookTitle={findRelease.title}
          bookAuthor={findRelease.author}
          mediaType={findRelease.mediaType}
        />
      )}
    </div>
  );
}
