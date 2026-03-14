import { BookOpen, Headphones } from "lucide-react";
import type { Book } from "@/api/client";

export default function BookCard({ book }: { book: Book }) {
  const isAudiobook = book.media_type === "audiobook";

  return (
    <div className="group bg-gray-900 rounded-lg overflow-hidden border border-gray-800 hover:border-indigo-500/50 transition-colors">
      {/* Cover */}
      <div className="aspect-[2/3] bg-gray-800 flex items-center justify-center relative">
        {book.cover_path ? (
          <img
            src={book.cover_path}
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
              : "bg-indigo-500/20 text-indigo-400"
          }`}
        >
          {isAudiobook ? "Audio" : "eBook"}
        </span>
      </div>

      {/* Info */}
      <div className="p-3">
        <h3 className="text-sm font-medium text-gray-100 truncate">
          {book.title}
        </h3>
        <p className="text-xs text-gray-400 truncate mt-1">{book.author}</p>
      </div>
    </div>
  );
}
