import { X } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface BulkAction {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
  variant?: "danger" | "primary" | "default";
}

interface BulkActionBarProps {
  selectedCount: number;
  onClearSelection: () => void;
  actions: BulkAction[];
}

const variantClasses: Record<string, string> = {
  danger: "text-red-400 hover:bg-red-500/20",
  primary: "text-indigo-400 hover:bg-indigo-500/20",
  default: "text-gray-300 hover:bg-gray-700",
};

export default function BulkActionBar({ selectedCount, onClearSelection, actions }: BulkActionBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-gray-800 border-t border-gray-700 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center gap-3">
        <button
          onClick={onClearSelection}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          <X size={14} />
          Clear selection
        </button>
        <span className="text-sm text-gray-400">
          {selectedCount} selected
        </span>
        <div className="ml-auto flex items-center gap-2">
          {actions.map((action) => {
            const Icon = action.icon;
            const cls = variantClasses[action.variant ?? "default"];
            return (
              <button
                key={action.label}
                onClick={action.onClick}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${cls}`}
              >
                <Icon size={14} />
                {action.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
