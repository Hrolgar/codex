import { Download, Inbox } from "lucide-react";

export default function DownloadsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Downloads</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Manage your download queue
        </p>
      </div>

      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-2xl bg-gray-800/50 flex items-center justify-center mb-5">
          <Inbox size={28} className="text-gray-600" />
        </div>
        <h3 className="text-lg font-medium text-gray-300 mb-2">
          No active downloads
        </h3>
        <p className="text-sm text-gray-500 max-w-xs">
          When you find books to download, they'll appear here with progress
          tracking.
        </p>
        <div className="mt-8 bg-gray-900 border border-gray-800 rounded-lg p-4 max-w-sm w-full">
          <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
            Coming in Phase 2
          </h4>
          <ul className="space-y-2 text-sm text-gray-500">
            <li className="flex items-center gap-2">
              <Download size={14} className="text-gray-600" />
              Download queue with live progress
            </li>
            <li className="flex items-center gap-2">
              <Download size={14} className="text-gray-600" />
              Prowlarr integration for search
            </li>
            <li className="flex items-center gap-2">
              <Download size={14} className="text-gray-600" />
              Duplicate detection before download
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
