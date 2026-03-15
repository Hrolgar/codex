import { Link } from "react-router-dom";
import { BookOpen, Headphones } from "lucide-react";
import type { BookListItem } from "@/api/client";

export default function BookCard({ book }: { book: BookListItem }) {
  const isAudiobook = book.media_type === "audiobook";
  const isComic = book.media_type === "comic";

  return (
    <Link
      to={`/books/${book.id}`}
      className="group bg-gray-900 rounded-lg overflow-hidden border border-gray-800 hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/5 transition-all duration-200"
    >
      {/* Cover */}
      <div className="aspect-[2/3] bg-gray-800 flex items-center justify-center relative">
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt={book.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-600">
            {isAudiobook ? <Headphones size={32} /> : <BookOpen size={32} />}
          </div>
        )}
        {/* Media type badge */}
        <span
          className={`absolute top-2 right-2 px-2 py-0.5 rounded text-xs font-medium ${
            isAudiobook
              ? "bg-purple-500/20 text-purple-400"
              : isComic
                ? "bg-green-500/20 text-green-400"
                : "bg-indigo-500/20 text-indigo-400"
          }`}
        >
          {isAudiobook ? "Audio" : isComic ? "Comic" : "eBook"}
        </span>
        {/* Owned indicator */}
        {book.owned != null && (
          <span
            className={`absolute top-2 left-2 w-3 h-3 rounded-full border-2 border-gray-900 ${
              book.owned ? "bg-green-400" : "bg-gray-500"
            }`}
            title={book.owned ? "In Library" : "Missing"}
          />
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        <h3 className="text-sm font-medium text-gray-100 truncate">
          {book.title}
        </h3>
        <p className="text-xs text-gray-400 truncate mt-1">
          {book.author ?? "Unknown author"}
        </p>
        {book.publish_year && (
          <p className="text-xs text-gray-500 mt-0.5">{book.publish_year}</p>
        )}
      </div>
    </Link>
  );
}
