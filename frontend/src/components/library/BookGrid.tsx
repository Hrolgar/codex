import type { BookListItem } from "@/api/client";
import BookCard from "./BookCard";

interface BookGridProps {
  books: BookListItem[];
  isLoading?: boolean;
}

export default function BookGrid({ books, isLoading }: BookGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="bg-gray-900 rounded-lg overflow-hidden border border-gray-800 animate-pulse">
            <div className="aspect-[2/3] bg-gray-800" />
            <div className="p-3 space-y-2">
              <div className="h-3 bg-gray-800 rounded w-3/4" />
              <div className="h-2 bg-gray-800 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (books.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p className="text-lg">No books found</p>
        <p className="text-sm mt-1">Add a library in Settings to get started</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {books.map((book) => (
        <BookCard key={book.id} book={book} />
      ))}
    </div>
  );
}
