import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { addAuthor } from "@/api/client";
import { X, Loader2 } from "lucide-react";

interface AddAuthorModalProps {
  open: boolean;
  onClose: () => void;
}

export default function AddAuthorModal({ open, onClose }: AddAuthorModalProps) {
  const [name, setName] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (authorName: string) => addAuthor(authorName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authors"] });
      setName("");
      onClose();
    },
  });

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed) mutation.mutate(trimmed);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-md p-6">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-200 transition-colors"
        >
          <X size={18} />
        </button>

        <h2 className="text-lg font-semibold text-gray-100 mb-4">
          Add Author
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Author name..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />

          {mutation.isError && (
            <p className="text-sm text-red-400">
              Failed to add author. Please try again.
            </p>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || mutation.isPending}
              className="px-4 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2"
            >
              {mutation.isPending && <Loader2 size={14} className="animate-spin" />}
              Add Author
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
