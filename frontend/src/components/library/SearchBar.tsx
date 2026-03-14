import { useEffect, useState } from "react";
import { Search } from "lucide-react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  onMediaTypeChange: (type: string) => void;
  mediaType: string;
}

export default function SearchBar({
  onSearch,
  onMediaTypeChange,
  mediaType,
}: SearchBarProps) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => onSearch(query), 300);
    return () => clearTimeout(timer);
  }, [query, onSearch]);

  const mediaTypes = [
    { value: "", label: "All" },
    { value: "ebook", label: "eBooks" },
    { value: "audiobook", label: "Audiobooks" },
  ];

  return (
    <div className="flex flex-col sm:flex-row gap-3">
      <div className="relative flex-1">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
        />
        <input
          type="text"
          placeholder="Search books..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
        {mediaTypes.map((t) => (
          <button
            key={t.value}
            onClick={() => onMediaTypeChange(t.value)}
            className={`px-3 py-1 rounded text-sm transition-colors ${
              mediaType === t.value
                ? "bg-indigo-500 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}
