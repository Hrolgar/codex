import type { BookListItem } from "@/api/client";
import { SearchX } from "lucide-react";
import BookCard from "./BookCard";

interface BookGridProps {
  books: BookListItem[];
  isLoading?: boolean;
  selectedBookIds?: Set<string>;
  onToggleSelected?: (bookId: string) => void;
}

export default function BookGrid({ books, isLoading, selectedBookIds, onToggleSelected }: BookGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="bg-gray-900 rounded-lg overflow-hidden border border-gray-800"
          >
            <div className="aspect-[2/3] skeleton" />
            <div className="p-3 space-y-2">
              <div className="h-3 skeleton rounded w-3/4" />
              <div className="h-2 skeleton rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (books.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <SearchX size={32} className="text-gray-700 mb-3" />
        <p className="text-gray-400">No books found</p>
        <p className="text-sm text-gray-600 mt-1">
          Try adjusting your search or filters
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {books.map((book) => (
        <div key={book.id} className="relative">
          {onToggleSelected && (
            <label className="absolute top-2 left-2 z-10 cursor-pointer" onClick={(e) => e.stopPropagation()}>
              <input
                type="checkbox"
                checked={selectedBookIds?.has(book.id) ?? false}
                onChange={() => onToggleSelected(book.id)}
                className="w-4 h-4 rounded border-gray-600 bg-gray-800/80 text-indigo-500 focus:ring-indigo-500/30"
              />
            </label>
          )}
          <BookCard book={book} />
        </div>
      ))}
    </div>
  );
}
