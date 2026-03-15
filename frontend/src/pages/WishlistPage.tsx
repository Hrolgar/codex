import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getWishlist,
  addToWishlist,
  removeFromWishlist,
  updateWishlistItem,
} from "@/api/client";
import type { WishlistItem } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import { Plus, Trash2, Star, Search, Download, CheckCircle, Clock, X } from "lucide-react";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  waiting: { label: "Waiting", color: "text-gray-400 bg-gray-500/10", icon: Clock },
  found: { label: "Found", color: "text-yellow-400 bg-yellow-500/10", icon: Search },
  downloading: { label: "Downloading", color: "text-indigo-400 bg-indigo-500/10", icon: Download },
  complete: { label: "Complete", color: "text-green-400 bg-green-500/10", icon: CheckCircle },
};

export default function WishlistPage() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ search_title: "", search_author: "", auto_download: true });

  const { data: items, isLoading } = useQuery({
    queryKey: ["wishlist"],
    queryFn: getWishlist,
  });

  const addMutation = useMutation({
    mutationFn: addToWishlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      setShowAdd(false);
      setForm({ search_title: "", search_author: "", auto_download: true });
      addToast("Added to wishlist");
    },
    onError: () => addToast("Failed to add to wishlist", "error"),
  });

  const removeMutation = useMutation({
    mutationFn: removeFromWishlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      addToast("Removed from wishlist");
    },
  });

  const toggleAutoDownload = useMutation({
    mutationFn: ({ id, auto_download }: { id: string; auto_download: boolean }) =>
      updateWishlistItem(id, { auto_download }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.search_title.trim()) return;
    addMutation.mutate({
      search_title: form.search_title.trim(),
      search_author: form.search_author.trim() || undefined,
      auto_download: form.auto_download,
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="h-8 w-32 skeleton rounded" />
          <div className="h-10 w-24 skeleton rounded" />
        </div>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 skeleton rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Wishlist</h1>
          <p className="text-sm text-gray-400 mt-1">
            {items?.length ?? 0} item{items?.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {showAdd ? <X size={16} /> : <Plus size={16} />}
          {showAdd ? "Cancel" : "Add Item"}
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <form
          onSubmit={handleSubmit}
          className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-4"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Title *</label>
              <input
                type="text"
                value={form.search_title}
                onChange={(e) => setForm({ ...form, search_title: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
                placeholder="Book title"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Author</label>
              <input
                type="text"
                value={form.search_author}
                onChange={(e) => setForm({ ...form, search_author: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
                placeholder="Author name"
              />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={form.auto_download}
                onChange={(e) => setForm({ ...form, auto_download: e.target.checked })}
                className="w-4 h-4 rounded border-gray-600 text-indigo-600 focus:ring-indigo-500 bg-gray-800"
              />
              Auto-download when found
            </label>
            <button
              type="submit"
              disabled={addMutation.isPending || !form.search_title.trim()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {addMutation.isPending ? "Adding..." : "Add to Wishlist"}
            </button>
          </div>
        </form>
      )}

      {/* Wishlist table */}
      {items && items.length > 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400">
                  <th className="text-left px-4 py-3 font-medium">Title</th>
                  <th className="text-left px-4 py-3 font-medium hidden sm:table-cell">Author</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-center px-4 py-3 font-medium">Auto DL</th>
                  <th className="text-right px-4 py-3 font-medium w-16"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <WishlistRow
                    key={item.id}
                    item={item}
                    onDelete={() => removeMutation.mutate(item.id)}
                    onToggleAuto={() =>
                      toggleAutoDownload.mutate({
                        id: item.id,
                        auto_download: !item.auto_download,
                      })
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Star size={32} className="text-gray-700 mb-3" />
          <p className="text-gray-400 text-lg">Your wishlist is empty</p>
          <p className="text-sm text-gray-600 mt-1">
            Add books you're looking for and they'll be automatically searched
          </p>
          <button
            onClick={() => setShowAdd(true)}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={16} />
            Add Your First Item
          </button>
        </div>
      )}
    </div>
  );
}

function WishlistRow({
  item,
  onDelete,
  onToggleAuto,
}: {
  item: WishlistItem;
  onDelete: () => void;
  onToggleAuto: () => void;
}) {
  const cfg = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.waiting;
  const Icon = cfg.icon;

  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
      <td className="px-4 py-3">
        <p className="text-gray-100 font-medium">{item.search_title}</p>
      </td>
      <td className="px-4 py-3 text-gray-400 hidden sm:table-cell">
        {item.search_author ?? "—"}
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${cfg.color}`}
        >
          <Icon size={12} />
          {cfg.label}
        </span>
      </td>
      <td className="px-4 py-3 text-center">
        <button
          onClick={onToggleAuto}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
            item.auto_download ? "bg-indigo-600" : "bg-gray-700"
          }`}
          title={item.auto_download ? "Auto-download on" : "Auto-download off"}
        >
          <span
            className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
              item.auto_download ? "translate-x-4.5" : "translate-x-1"
            }`}
          />
        </button>
      </td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={onDelete}
          className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
          title="Remove from wishlist"
        >
          <Trash2 size={14} />
        </button>
      </td>
    </tr>
  );
}
