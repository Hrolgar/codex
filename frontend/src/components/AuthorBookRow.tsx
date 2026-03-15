import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toggleBookMonitored } from '@/api/client';
import { Eye, EyeOff, Search, ChevronDown, ChevronRight } from 'lucide-react';

interface BookEdition {
  language: string;
  format: string;
  owned: boolean;
}

interface AuthorBook {
  id: string;
  title: string;
  author: string | null;
  media_type: string;
  cover_url: string | null;
  isbn_13: string | null;
  publish_year: number | null;
  owned: boolean;
  monitored: boolean;
  editions?: BookEdition[];
}

interface Props {
  book: AuthorBook;
  authorName: string;
  onSearch: (title: string, author: string, mediaType: string) => void;
}

const FORMAT_BADGES: Record<string, { label: string; color: string }> = {
  ebook: { label: 'EPUB', color: 'bg-blue-500/20 text-blue-400' },
  audiobook: { label: 'AUDIO', color: 'bg-orange-500/20 text-orange-400' },
  comic: { label: 'COMIC', color: 'bg-green-500/20 text-green-400' },
};

export default function AuthorBookRow({ book, authorName, onSearch }: Props) {
  const [expanded, setExpanded] = useState(false);
  const queryClient = useQueryClient();
  const badge = FORMAT_BADGES[book.media_type] ?? FORMAT_BADGES.ebook;

  const monitorMutation = useMutation({
    mutationFn: () => toggleBookMonitored(book.id, !book.monitored),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['author'] }),
  });

  const status = book.owned
    ? { label: 'Owned', color: 'text-green-400' }
    : !book.monitored
      ? { label: 'Not Monitored', color: 'text-gray-500' }
      : { label: 'Missing', color: 'text-yellow-400' };

  return (
    <div className='border-b border-gray-800/50 last:border-0'>
      <div className='flex items-center gap-3 px-4 py-3 hover:bg-gray-800/30 transition-colors'>
        {/* Expand toggle */}
        <button onClick={() => setExpanded(!expanded)} className='text-gray-600 hover:text-gray-400 shrink-0'>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        {/* Cover */}
        <Link to={`/books/${book.id}`} className='w-8 h-11 rounded bg-gray-800 overflow-hidden shrink-0'>
          {book.cover_url ? (
            <img src={book.cover_url} alt={book.title} className='w-full h-full object-cover' />
          ) : (
            <div className='w-full h-full flex items-center justify-center text-gray-600 text-[10px]'>?</div>
          )}
        </Link>

        {/* Title + format */}
        <div className='flex-1 min-w-0'>
          <Link to={`/books/${book.id}`} className='text-sm text-gray-100 truncate block hover:text-indigo-400 transition-colors'>{book.title}</Link>
          {book.publish_year && <span className='text-xs text-gray-600'>{book.publish_year}</span>}
        </div>

        <span className={'text-[10px] font-medium px-1.5 py-0.5 rounded ' + badge.color}>{badge.label}</span>
        <span className={'text-xs font-medium ' + status.color}>{status.label}</span>

        {/* Monitor toggle */}
        <button
          onClick={(e) => { e.stopPropagation(); monitorMutation.mutate(); }}
          disabled={monitorMutation.isPending}
          className='p-1 text-gray-500 hover:text-gray-300 transition-colors'
          title={book.monitored ? 'Unmonitor' : 'Monitor'}
        >
          {book.monitored ? <Eye size={14} /> : <EyeOff size={14} />}
        </button>

        {/* Search */}
        <button
          onClick={(e) => { e.stopPropagation(); onSearch(book.title, authorName, book.media_type); }}
          className='p-1 text-gray-500 hover:text-indigo-400 transition-colors'
          title='Find releases'
        >
          <Search size={14} />
        </button>
      </div>

      {/* Expanded editions */}
      {expanded && book.editions && book.editions.length > 0 && (
        <div className='pl-16 pr-4 pb-3 space-y-1'>
          {book.editions.map((ed, i) => (
            <div key={i} className='flex items-center gap-3 text-xs py-1 px-3 bg-gray-900/50 rounded'>
              <span className='font-mono text-gray-400 uppercase w-6'>{ed.language}</span>
              <span className='text-gray-500'>{ed.format}</span>
              {ed.owned ? (
                <span className='text-green-400'>Owned</span>
              ) : (
                <span className='text-gray-600'>Not Found</span>
              )}
              <button
                onClick={() => onSearch(book.title, authorName, book.media_type)}
                className='p-1 text-gray-600 hover:text-indigo-400 transition-colors ml-auto'
                title={'Search for ' + ed.language.toUpperCase() + ' edition'}
              >
                <Search size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {expanded && (!book.editions || book.editions.length === 0) && (
        <div className='pl-16 pr-4 pb-3'>
          <p className='text-xs text-gray-600 italic'>No edition data available</p>
        </div>
      )}
    </div>
  );
}
