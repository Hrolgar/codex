import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getLibraries,
  createLibrary,
  deleteLibrary,
  scanLibrary,
} from "@/api/client";
import {
  Plus,
  Trash2,
  RefreshCw,
  FolderOpen,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
} from "lucide-react";

type SidebarSection =
  | "general"
  | "search-mode"
  | "downloads"
  | "security"
  | "notifications"
  | "metadata-hardcover"
  | "metadata-openlibrary"
  | "metadata-googlebooks"
  | "advanced"
  | "prowlarr"
  | "audiobookbay"
  | "download-clients";

interface NavItem {
  id: SidebarSection;
  label: string;
  indent?: boolean;
}

interface NavHeader {
  header: string;
}

type NavEntry = NavItem | NavHeader | { id: string; label: string; submenu: NavItem[] };

function isHeader(e: NavEntry): e is NavHeader {
  return "header" in e;
}

function isSubmenu(e: NavEntry): e is { id: string; label: string; submenu: NavItem[] } {
  return "submenu" in e;
}

const NAV: NavEntry[] = [
  { id: "general", label: "General" },
  { id: "search-mode", label: "Search Mode" },
  { id: "downloads", label: "Downloads" },
  { id: "security", label: "Security" },
  { id: "notifications", label: "Notifications" },
  {
    id: "metadata",
    label: "Metadata Providers",
    submenu: [
      { id: "metadata-hardcover", label: "Hardcover", indent: true },
      { id: "metadata-openlibrary", label: "Open Library", indent: true },
      { id: "metadata-googlebooks", label: "Google Books", indent: true },
    ],
  },
  { id: "advanced", label: "Advanced" },
  { header: "RELEASE SOURCES" },
  { id: "prowlarr", label: "Prowlarr" },
  { id: "audiobookbay", label: "AudiobookBay" },
  { header: "DOWNLOAD CLIENTS" },
  { id: "download-clients", label: "Download Clients" },
];

/* ── General Section (Library Management) ─────────────────────── */

function GeneralSection() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [scannerType, setScannerType] = useState("filesystem");
  const [path, setPath] = useState("");
  const [url, setUrl] = useState("");
  const [apiKey, setApiKey] = useState("");

  const { data: libraries } = useQuery({
    queryKey: ["libraries"],
    queryFn: getLibraries,
  });

  const addMutation = useMutation({
    mutationFn: createLibrary,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      setName("");
      setPath("");
      setUrl("");
      setApiKey("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteLibrary,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["libraries"] }),
  });

  const scanMutation = useMutation({ mutationFn: scanLibrary });

  const isFormValid =
    name.trim() !== "" &&
    (scannerType === "filesystem"
      ? path.trim() !== ""
      : url.trim() !== "" && apiKey.trim() !== "");

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (scannerType === "filesystem") {
      addMutation.mutate({ name, scanner_type: scannerType, path });
    } else {
      addMutation.mutate({ name, scanner_type: scannerType, url, api_key: apiKey });
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-100">General</h2>

      {/* Libraries */}
      <div>
        <h3 className="text-lg font-semibold text-gray-200 mb-3">Libraries</h3>
        <div className="space-y-2">
          {libraries?.map((lib) => (
            <div
              key={lib.id}
              className="flex items-center justify-between bg-gray-800/50 border border-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center gap-3">
                <FolderOpen size={18} className="text-indigo-400" />
                <div>
                  <p className="text-sm font-medium text-gray-100">
                    {lib.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {lib.scanner_type}
                    {" · "}
                    <span
                      className={
                        lib.scan_status === "scanning"
                          ? "text-yellow-400"
                          : lib.scan_status === "error"
                            ? "text-red-400"
                            : "text-gray-500"
                      }
                    >
                      {lib.scan_status}
                    </span>
                    {lib.last_scan_at && (
                      <>
                        {" · last scan "}
                        {new Date(lib.last_scan_at).toLocaleString()}
                      </>
                    )}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => scanMutation.mutate(lib.id)}
                  disabled={scanMutation.isPending}
                  className="p-2 text-gray-400 hover:text-indigo-400 transition-colors"
                  title="Scan library"
                >
                  <RefreshCw
                    size={16}
                    className={scanMutation.isPending ? "animate-spin" : ""}
                  />
                </button>
                <button
                  onClick={() => deleteMutation.mutate(lib.id)}
                  className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                  title="Delete library"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
          {libraries?.length === 0 && (
            <p className="text-sm text-gray-500">No libraries configured</p>
          )}
        </div>
      </div>

      {/* Add Library Form */}
      <form onSubmit={handleAdd} className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-200">Add Library</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Scanner Type
            </label>
            <select
              value={scannerType}
              onChange={(e) => setScannerType(e.target.value)}
              className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="filesystem">Filesystem</option>
              <option value="audiobookshelf">Audiobookshelf</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>
        {scannerType === "filesystem" && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">Path</label>
            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/path/to/books"
              required
              className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
        )}
        {scannerType === "audiobookshelf" && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">URL</label>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="http://audiobookshelf.local:13378"
                required
                className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
                className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        )}
        <button
          type="submit"
          disabled={addMutation.isPending || !isFormValid}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          <Plus size={16} />
          Add Library
        </button>
      </form>
    </div>
  );
}

/* ── Hardcover Section ────────────────────────────────────────── */

function HardcoverSection() {
  const [enabled, setEnabled] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-100">Hardcover</h2>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setEnabled(!enabled)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            enabled ? "bg-indigo-500" : "bg-gray-700"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
        <span className="text-sm text-gray-300">Enable Hardcover</span>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">API Key</label>
        <div className="relative">
          <input
            type={showKey ? "text" : "password"}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full px-3 py-2 pr-10 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
          >
            {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </div>

      <button
        onClick={() => {
          setTesting(true);
          setTimeout(() => setTesting(false), 1500);
        }}
        disabled={testing || !apiKey.trim()}
        className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
      >
        {testing ? "Testing..." : "Test Connection"}
      </button>
    </div>
  );
}

/* ── Prowlarr Section ─────────────────────────────────────────── */

function ProwlarrSection() {
  const [enabled, setEnabled] = useState(false);
  const [prowlarrUrl, setProwlarrUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-100">Prowlarr</h2>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setEnabled(!enabled)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            enabled ? "bg-indigo-500" : "bg-gray-700"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
        <span className="text-sm text-gray-300">Enable Prowlarr</span>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">URL</label>
        <input
          type="text"
          value={prowlarrUrl}
          onChange={(e) => setProwlarrUrl(e.target.value)}
          placeholder="http://prowlarr:9696"
          className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
        />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">API Key</label>
        <div className="relative">
          <input
            type={showKey ? "text" : "password"}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full px-3 py-2 pr-10 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
          >
            {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </div>

      <button
        onClick={() => {
          setTesting(true);
          setTimeout(() => setTesting(false), 1500);
        }}
        disabled={testing || !prowlarrUrl.trim() || !apiKey.trim()}
        className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
      >
        {testing ? "Testing..." : "Test Connection"}
      </button>
    </div>
  );
}

/* ── Placeholder Section ──────────────────────────────────────── */

function PlaceholderSection({ title }: { title: string }) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-gray-100">{title}</h2>
      <p className="text-sm text-gray-500">Coming soon</p>
    </div>
  );
}

/* ── Sidebar Nav ──────────────────────────────────────────────── */

function Sidebar({
  active,
  onSelect,
}: {
  active: SidebarSection;
  onSelect: (s: SidebarSection) => void;
}) {
  const [metadataOpen, setMetadataOpen] = useState(
    active.startsWith("metadata-")
  );

  const isMetadataActive = active.startsWith("metadata-");

  return (
    <nav className="w-56 shrink-0 bg-gray-950 border-r border-gray-800 py-4 overflow-y-auto">
      {NAV.map((entry) => {
        if (isHeader(entry)) {
          return (
            <div
              key={entry.header}
              className="px-4 pt-5 pb-1 text-xs font-semibold uppercase tracking-wider text-gray-600 select-none"
            >
              {entry.header}
            </div>
          );
        }

        if (isSubmenu(entry)) {
          const open = metadataOpen;
          return (
            <div key={entry.id}>
              <button
                onClick={() => setMetadataOpen(!open)}
                className={`w-full flex items-center gap-2 px-4 py-2 text-sm text-left transition-colors ${
                  isMetadataActive
                    ? "text-white border-l-2 border-indigo-500 bg-gray-900/50"
                    : "text-gray-400 border-l-2 border-transparent hover:text-gray-200 hover:bg-gray-900/30"
                }`}
              >
                {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                {entry.label}
              </button>
              {open &&
                entry.submenu.map((sub) => (
                  <button
                    key={sub.id}
                    onClick={() => onSelect(sub.id)}
                    className={`w-full text-left pl-10 pr-4 py-1.5 text-sm transition-colors ${
                      active === sub.id
                        ? "text-white border-l-2 border-indigo-500 bg-gray-900/50"
                        : "text-gray-400 border-l-2 border-transparent hover:text-gray-200 hover:bg-gray-900/30"
                    }`}
                  >
                    {sub.label}
                  </button>
                ))}
            </div>
          );
        }

        const item = entry as NavItem;
        return (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className={`w-full text-left px-4 py-2 text-sm transition-colors ${
              active === item.id
                ? "text-white border-l-2 border-indigo-500 bg-gray-900/50"
                : "text-gray-400 border-l-2 border-transparent hover:text-gray-200 hover:bg-gray-900/30"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </nav>
  );
}

/* ── Content Router ───────────────────────────────────────────── */

function SectionContent({ section }: { section: SidebarSection }) {
  switch (section) {
    case "general":
      return <GeneralSection />;
    case "metadata-hardcover":
      return <HardcoverSection />;
    case "prowlarr":
      return <ProwlarrSection />;
    case "search-mode":
      return <PlaceholderSection title="Search Mode" />;
    case "downloads":
      return <PlaceholderSection title="Downloads" />;
    case "security":
      return <PlaceholderSection title="Security" />;
    case "notifications":
      return <PlaceholderSection title="Notifications" />;
    case "metadata-openlibrary":
      return <PlaceholderSection title="Open Library" />;
    case "metadata-googlebooks":
      return <PlaceholderSection title="Google Books" />;
    case "advanced":
      return <PlaceholderSection title="Advanced" />;
    case "audiobookbay":
      return <PlaceholderSection title="AudiobookBay" />;
    case "download-clients":
      return <PlaceholderSection title="Download Clients" />;
    default:
      return <PlaceholderSection title="Settings" />;
  }
}

/* ── Main Page ────────────────────────────────────────────────── */

export default function SettingsPage() {
  const [active, setActive] = useState<SidebarSection>("general");

  return (
    <div className="flex h-full min-h-0 -m-6">
      <Sidebar active={active} onSelect={setActive} />
      <div className="flex-1 overflow-y-auto bg-gray-900 p-8">
        <SectionContent section={active} />
      </div>
    </div>
  );
}
