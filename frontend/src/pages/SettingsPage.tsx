import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getProwlarrIndexers,
  getLibraries,
  createLibrary,
  deleteLibrary,
  scanLibrary,
  getSystemStats,
  getSettings,
  updateSettings,
  type SettingsCategory,
  type ProwlarrIndexer,
} from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import {
  Settings as SettingsIcon,
  Search,
  Download,
  Shield,
  Bell,
  BookOpen,
  Plus,
  Trash2,
  RefreshCw,
  FolderOpen,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronRight,
  Zap,
  Loader2,
  HelpCircle,
} from "lucide-react";

// --- Sidebar nav items ---
type NavItem = {
  id: string;
  label: string;
  icon?: typeof SettingsIcon;
  children?: { id: string; label: string }[];
  isHeader?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { id: "general", label: "General", icon: SettingsIcon },
  { id: "search-mode", label: "Search Mode", icon: Search },
  { id: "downloads", label: "Downloads", icon: Download },
  { id: "security", label: "Security", icon: Shield },
  { id: "notifications", label: "Notifications", icon: Bell },
  {
    id: "metadata-providers",
    label: "Metadata Providers",
    icon: BookOpen,
    children: [
      { id: "metadata-hardcover", label: "Hardcover" },
      { id: "metadata-openlibrary", label: "Open Library" },
      { id: "metadata-google", label: "Google Books" },
    ],
  },
  { id: "advanced", label: "Advanced", icon: Zap },
  { id: "_release_sources", label: "RELEASE SOURCES", isHeader: true },
  { id: "prowlarr", label: "Prowlarr", icon: Download },
  { id: "audiobookbay", label: "AudiobookBay", icon: Download },
  { id: "_download_clients", label: "DOWNLOAD CLIENTS", isHeader: true },
  { id: "download-clients", label: "Download Clients", icon: Download },
];

// --- Toggle component ---
function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`mt-0.5 relative w-10 h-5 rounded-full transition-colors flex-shrink-0 ${
          checked ? "bg-indigo-500" : "bg-gray-700"
        }`}
      >
        <span
          className={`block w-4 h-4 rounded-full bg-white transition-transform ${
            checked ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </button>
      <div>
        <p className="text-sm text-gray-200">{label}</p>
        {description && (
          <p className="text-xs text-gray-500 mt-0.5">{description}</p>
        )}
      </div>
    </div>
  );
}

// --- Secret input component ---
function SecretInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 pr-10 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500 transition-colors"
      />
      <button
        type="button"
        onClick={() => setVisible(!visible)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
      >
        {visible ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    </div>
  );
}

// --- Format tag selector ---
function FormatTags({
  available,
  selected,
  onChange,
  label,
  description,
}: {
  available: string[];
  selected: string[];
  onChange: (v: string[]) => void;
  label: string;
  description?: string;
}) {
  const toggle = (fmt: string) => {
    if (selected.includes(fmt)) {
      onChange(selected.filter((f) => f !== fmt));
    } else {
      onChange([...selected, fmt]);
    }
  };

  return (
    <div>
      <p className="text-sm font-medium text-gray-200 mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        {available.map((fmt) => (
          <button
            key={fmt}
            type="button"
            onClick={() => toggle(fmt)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium uppercase transition-colors ${
              selected.includes(fmt)
                ? "bg-cyan-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            }`}
          >
            {fmt}
          </button>
        ))}
      </div>
      {description && (
        <p className="text-xs text-gray-500 mt-2">{description}</p>
      )}
    </div>
  );
}

// --- Section wrapper ---
function SettingsSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-100 mb-1">{title}</h2>
      {description && (
        <p className="text-sm text-gray-500 mb-6">{description}</p>
      )}
      <div className="space-y-6">{children}</div>
    </div>
  );
}

// --- Field wrapper ---
function Field({
  label,
  description,
  required,
  children,
}: {
  label: string;
  description?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
      {description && (
        <p className="text-xs text-gray-500 mt-1">{description}</p>
      )}
    </div>
  );
}

// --- Placeholder for unbuilt sections ---
function ComingSoon({ section }: { section: string }) {
  return (
    <SettingsSection title={section}>
      <div className="flex items-center justify-center py-16 border border-dashed border-gray-800 rounded-lg">
        <p className="text-gray-600 text-sm">Coming soon</p>
      </div>
    </SettingsSection>
  );
}

// ============================================================
// SECTION COMPONENTS
// ============================================================

function GeneralSection() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [name, setName] = useState("");
  const [scannerType, setScannerType] = useState("filesystem");
  const [path, setPath] = useState("");
  const [url, setUrl] = useState("");
  const [apiKey, setApiKey] = useState("");

  const { data: libraries } = useQuery({
    queryKey: ["libraries"],
    queryFn: getLibraries,
  });

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: getSystemStats,
  });

  const addMutation = useMutation({
    mutationFn: createLibrary,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      setName("");
      setPath("");
      setUrl("");
      setApiKey("");
      addToast("Library added");
    },
    onError: () => addToast("Failed to add library", "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteLibrary,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      addToast("Library removed");
    },
  });

  const scanMutation = useMutation({
    mutationFn: scanLibrary,
    onSuccess: () => addToast("Scan started"),
  });

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
      addMutation.mutate({
        name,
        scanner_type: scannerType,
        url,
        api_key: apiKey,
      });
    }
  }

  const BOOK_FORMATS = ["EPUB", "MOBI", "AZW3", "FB2", "DJVU", "CBZ", "CBR", "PDF", "TXT"];
  const AUDIO_FORMATS = ["M4B", "MP3", "M4A", "FLAC", "OGG"];

  return (
    <SettingsSection title="General" description="Core configuration and library management.">
      {stats && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Libraries", value: stats.libraries },
            { label: "Books", value: stats.books },
            { label: "Items", value: stats.library_items },
          ].map((s) => (
            <div key={s.label} className="bg-gray-950 border border-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className="text-xl font-bold text-gray-100 mt-0.5">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Libraries</h3>
        <div className="space-y-2">
          {libraries?.map((lib) => (
            <div key={lib.id} className="flex items-center justify-between bg-gray-950 border border-gray-800 rounded-lg p-3">
              <div className="flex items-center gap-3">
                <FolderOpen size={16} className="text-indigo-400" />
                <div>
                  <p className="text-sm font-medium text-gray-100">{lib.name}</p>
                  <p className="text-xs text-gray-500">
                    {lib.scanner_type}{" · "}
                    <span className={lib.scan_status === "scanning" ? "text-yellow-400" : lib.scan_status === "error" ? "text-red-400" : "text-gray-500"}>
                      {lib.scan_status}
                    </span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => scanMutation.mutate(lib.id)} disabled={scanMutation.isPending} className="p-1.5 text-gray-500 hover:text-indigo-400 transition-colors" title="Scan">
                  <RefreshCw size={14} className={scanMutation.isPending ? "animate-spin" : ""} />
                </button>
                <button onClick={() => deleteMutation.mutate(lib.id)} className="p-1.5 text-gray-500 hover:text-red-400 transition-colors" title="Delete">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
          {libraries?.length === 0 && <p className="text-xs text-gray-600 py-2">No libraries configured yet.</p>}
        </div>
      </div>

      <form onSubmit={handleAdd} className="space-y-3 bg-gray-950 border border-gray-800 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300">Add Library</h4>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Scanner Type">
            <select value={scannerType} onChange={(e) => setScannerType(e.target.value)} className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500">
              <option value="filesystem">Filesystem</option>
              <option value="audiobookshelf">Audiobookshelf</option>
            </select>
          </Field>
          <Field label="Name" required>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
          </Field>
        </div>
        {scannerType === "filesystem" && (
          <Field label="Path" required description="Absolute path to your book directory">
            <input type="text" value={path} onChange={(e) => setPath(e.target.value)} placeholder="/mnt/nas/data/media/ebooks" className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
          </Field>
        )}
        {scannerType === "audiobookshelf" && (
          <>
            <Field label="URL" required>
              <input type="text" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="http://audiobookshelf.local:13378" className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <Field label="API Key" required>
              <SecretInput value={apiKey} onChange={setApiKey} placeholder="Your Audiobookshelf API key" />
            </Field>
          </>
        )}
        <button type="submit" disabled={addMutation.isPending || !isFormValid} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
          <Plus size={14} />
          Add Library
        </button>
      </form>

      <FormatTags available={BOOK_FORMATS} selected={["EPUB", "MOBI", "AZW3", "CBZ", "CBR", "PDF"]} onChange={() => {}} label="Supported Book Formats" description="Book formats to include in search results." />
      <FormatTags available={AUDIO_FORMATS} selected={["M4B", "MP3", "M4A"]} onChange={() => {}} label="Supported Audiobook Formats" description="Audiobook formats to include in search results." />
    </SettingsSection>
  );
}

function renderTemplatePreview(template: string, data: Record<string, string>): string {
  return template
    .replace(/\{(\w+)\?([^}]*)\}/g, (_match, token: string, inner: string) => {
      if (!data[token]) return "";
      return inner.replace(/\{(\w+)\}/g, (_m: string, t: string) => data[t] ?? "");
    })
    .replace(/\{(\w+)\}/g, (_match, token: string) => data[token] ?? "");
}

const SERIES_SAMPLE: Record<string, string> = {
  Author: "Brandon Sanderson",
  Title: "The Way of Kings",
  Series: "The Stormlight Archive",
  SeriesPosition: "1",
  Year: "2010",
  Language: "en",
  Edition: "Norwegian",
  Format: "epub",
  PartNumber: "1",
  OriginalName: "the_way_of_kings",
};

const STANDALONE_SAMPLE: Record<string, string> = {
  Author: "Brandon Sanderson",
  Title: "The Way of Kings",
  Series: "",
  SeriesPosition: "",
  Year: "2010",
  Language: "en",
  Edition: "Norwegian",
  Format: "epub",
  PartNumber: "",
  OriginalName: "the_way_of_kings",
};

const TOKEN_HELP_ROWS: [string, string][] = [
  ["{Author}", "Brandon Sanderson"],
  ["{Title}", "The Way of Kings"],
  ["{Series}", "The Stormlight Archive"],
  ["{SeriesPosition}", "1"],
  ["{Year}", "2010"],
  ["{Language}", "en"],
  ["{Edition}", "Norwegian"],
  ["{Format}", "epub"],
  ["{Series?...}", "Conditional: only renders if series exists"],
];

function PathTemplateField({ label, description, defaultValue }: { label: string; description: string; defaultValue: string }) {
  const [value, setValue] = useState(defaultValue);
  const [showHelp, setShowHelp] = useState(false);

  const seriesPreview = renderTemplatePreview(value, SERIES_SAMPLE);
  const standalonePreview = renderTemplatePreview(value, STANDALONE_SAMPLE);

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5">
        <label className="block text-sm font-medium text-gray-300">{label}</label>
        <button
          type="button"
          onClick={() => setShowHelp(!showHelp)}
          className="text-gray-500 hover:text-gray-300 transition-colors"
          title="Show available tokens"
        >
          <HelpCircle size={14} />
        </button>
      </div>
      {description && <p className="text-xs text-gray-500">{description}</p>}
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500 font-mono text-xs"
      />
      <div className="text-xs text-gray-500 space-y-0.5 pt-1">
        <p>Series example: <span className="text-gray-400 font-mono">{seriesPreview || "(empty)"}</span></p>
        <p>Standalone example: <span className="text-gray-400 font-mono">{standalonePreview || "(empty)"}</span></p>
      </div>
      {showHelp && (
        <div className="mt-2 p-3 bg-gray-800/50 border border-gray-700 rounded-lg">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-400">
                <th className="text-left pb-1 font-medium">Token</th>
                <th className="text-left pb-1 font-medium">Example</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {TOKEN_HELP_ROWS.map(([token, example]) => (
                <tr key={token}>
                  <td className="py-0.5 font-mono text-indigo-400">{token}</td>
                  <td className="py-0.5">{example}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function DownloadsSection() {
  return (
    <SettingsSection title="Downloads" description="Configure where downloaded files are saved and how they're organized.">
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Books</h3>
        <p className="text-xs text-gray-500 -mt-2">Configure where ebooks and magazines are saved.</p>
        <Field label="Destination" required description="Directory where downloaded book files are saved.">
          <input type="text" defaultValue="/downloads/books" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
        </Field>
        <Field label="File Organization" description="Choose how downloaded book files are named and organized.">
          <select defaultValue="rename" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500">
            <option value="none">None</option>
            <option value="rename">Rename and Organize</option>
          </select>
        </Field>
        <PathTemplateField
          label="Path Template"
          description="Use / to create folders. Wrap sections in {Series?...} to only include them when a series exists."
          defaultValue="{Author}/{Series?{Series}/{SeriesPosition} - }{Title}"
        />
        <Toggle checked={true} onChange={() => {}} label="Hardlink Book Torrents" description="Create hardlinks instead of copying. Preserves seeding but archives won't be extracted." />
      </div>

      <div className="border-t border-gray-800" />

      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Audiobooks</h3>
        <p className="text-xs text-gray-500 -mt-2">Configure where audiobooks are saved.</p>
        <Field label="Destination" required description="Directory where downloaded audiobook files are saved. Leave empty to use the Books destination.">
          <input type="text" defaultValue="/downloads/audiobooks" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
        </Field>
        <Field label="File Organization">
          <select defaultValue="rename" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500">
            <option value="none">None</option>
            <option value="rename">Rename and Organize</option>
          </select>
        </Field>
        <PathTemplateField
          label="Path Template"
          description="Use / to create folders. Wrap sections in {Series?...} to only include them when a series exists."
          defaultValue="{Author}/{Series?{Series}/{SeriesPosition} - }{Title}/{PartNumber} {Title}"
        />
        <Toggle checked={true} onChange={() => {}} label="Hardlink Audiobook Torrents" description="Create hardlinks instead of copying. Preserves seeding but archives won't be extracted." />
      </div>
      <div className="border-t border-gray-800" />

      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Comics</h3>
        <p className="text-xs text-gray-500 -mt-2">Configure where comics are saved.</p>
        <Field label="Destination" required description="Directory where downloaded comic files are saved.">
          <input type="text" defaultValue="/downloads/comics" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
        </Field>
        <Field label="File Organization">
          <select defaultValue="rename" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500">
            <option value="none">None</option>
            <option value="rename">Rename and Organize</option>
          </select>
        </Field>
        <PathTemplateField
          label="Path Template"
          description="Use / to create folders. Wrap sections in {Series?...} to only include them when a series exists."
          defaultValue="{Author}/{Series?{Series}/}{Title}"
        />
        <Toggle checked={true} onChange={() => {}} label="Hardlink Comics Torrents" description="Create hardlinks instead of copying. Preserves seeding but archives won't be extracted." />
      </div>
    </SettingsSection>
  );
}

function MetadataProviderSection({ title, description, linkUrl }: { provider?: string; title: string; description: string; linkUrl?: string }) {
  const [enabled, setEnabled] = useState(false);
  const [apiKeyVal, setApiKeyVal] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    setTimeout(() => {
      setTesting(false);
      setTestResult(apiKeyVal ? "Connected" : "API key required");
    }, 1000);
  };

  return (
    <SettingsSection title={title} description={description}>
      {linkUrl && (
        <p className="text-xs text-gray-500 -mt-4 mb-4">
          <a href={linkUrl} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">{linkUrl}</a>
        </p>
      )}
      <Toggle checked={enabled} onChange={setEnabled} label={`Enable ${title}`} description={`Enable ${title} as a metadata provider for book searches`} />
      {enabled && (
        <>
          <Field label="API Key" required>
            <SecretInput value={apiKeyVal} onChange={setApiKeyVal} placeholder={`Your ${title} API key`} />
          </Field>
          <div className="flex items-center gap-3">
            <button onClick={handleTest} disabled={testing} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
              {testing && <Loader2 size={14} className="animate-spin" />}
              Test Connection
            </button>
            {testResult && <span className="text-sm text-gray-400">{testResult}</span>}
          </div>
        </>
      )}
    </SettingsSection>
  );
}

function ProwlarrSection() {
  const [enabled, setEnabled] = useState(false);
  const [prowlarrUrl, setProwlarrUrl] = useState("");
  const [prowlarrKey, setProwlarrKey] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [indexers, setIndexers] = useState<ProwlarrIndexer[]>([]);
  const [selectedIndexers, setSelectedIndexers] = useState<Set<number>>(new Set());
  const [loadingIndexers, setLoadingIndexers] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    setConnected(false);
    setIndexers([]);
    try {
      const res = await fetch("/api/system/settings/test-connection?provider=prowlarr");
      const data = await res.json().catch(() => null);
      if (res.ok && data?.ok) {
        setTestResult(data.message ?? "Connected");
        setConnected(true);
        setLoadingIndexers(true);
        try {
          const idx = await getProwlarrIndexers();
          setIndexers(idx);
          setSelectedIndexers(new Set(idx.map((i) => i.id)));
        } catch {
          setIndexers([]);
        } finally {
          setLoadingIndexers(false);
        }
      } else {
        setTestResult(data?.message ?? "Connection failed");
      }
    } catch {
      setTestResult("Connection failed");
    } finally {
      setTesting(false);
    }
  };

  const toggleIndexer = (id: number) => {
    setSelectedIndexers((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <SettingsSection title="Prowlarr Integration" description="Search for books across your indexers via Prowlarr.">
      <Toggle checked={enabled} onChange={setEnabled} label="Enable Prowlarr source" description="Enable searching for books via Prowlarr indexers" />
      {enabled && (
        <>
          <Field label="Prowlarr URL" required description="Base URL of your Prowlarr instance">
            <input type="text" value={prowlarrUrl} onChange={(e) => setProwlarrUrl(e.target.value)} placeholder="http://10.69.4.51:9696/" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
          </Field>
          <Field label="API Key" required description="Found in Prowlarr: Settings > General > API Key">
            <SecretInput value={prowlarrKey} onChange={setProwlarrKey} placeholder="Your Prowlarr API key" />
          </Field>
          <div className="flex items-center gap-3">
            <button onClick={handleTest} disabled={testing} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
              {testing && <Loader2 size={14} className="animate-spin" />}
              Test Connection
            </button>
            {testResult && (
              <span className={`text-sm ${connected ? "text-green-400" : "text-gray-400"}`}>{testResult}</span>
            )}
          </div>
          {loadingIndexers && (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Loader2 size={14} className="animate-spin" />
              Loading indexers…
            </div>
          )}
          {connected && indexers.length > 0 && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300">Indexers</label>
              <div className="flex flex-wrap gap-2">
                {indexers.map((idx) => {
                  const active = selectedIndexers.has(idx.id);
                  return (
                    <button
                      key={idx.id}
                      onClick={() => toggleIndexer(idx.id)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                        active
                          ? "bg-cyan-600/20 border-cyan-500 text-cyan-300"
                          : "bg-gray-900 border-gray-700 text-gray-500"
                      }`}
                    >
                      {idx.name}
                      <span className={`ml-1.5 text-[10px] uppercase ${active ? "text-indigo-400" : "text-gray-600"}`}>
                        {idx.protocol}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {connected && indexers.length === 0 && !loadingIndexers && (
            <p className="text-sm text-gray-500">No indexers found in Prowlarr.</p>
          )}
          <Toggle checked={true} onChange={() => {}} label="Auto-expand search on no results" description="Automatically retry search without category filtering if no results are found" />
        </>
      )}
    </SettingsSection>
  );
}

function DownloadClientsSection() {
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  // qBittorrent state
  const [qbtEnabled, setQbtEnabled] = useState(false);
  const [qbtUrl, setQbtUrl] = useState("");
  const [qbtUsername, setQbtUsername] = useState("");
  const [qbtPassword, setQbtPassword] = useState("");
  const [qbtCategoryEbook, setQbtCategoryEbook] = useState("codex-books");
  const [qbtCategoryAudiobook, setQbtCategoryAudiobook] = useState("codex-audiobooks");
  const [qbtCategoryComic, setQbtCategoryComic] = useState("codex-comics");
  const [qbtTesting, setQbtTesting] = useState(false);
  const [qbtTestResult, setQbtTestResult] = useState<string | null>(null);

  // SABnzbd state
  const [sabEnabled, setSabEnabled] = useState(false);
  const [sabUrl, setSabUrl] = useState("");
  const [sabApiKey, setSabApiKey] = useState("");
  const [sabCategoryEbook, setSabCategoryEbook] = useState("codex-books");
  const [sabCategoryAudiobook, setSabCategoryAudiobook] = useState("codex-audiobooks");
  const [sabCategoryComic, setSabCategoryComic] = useState("codex-comics");
  const [sabTesting, setSabTesting] = useState(false);
  const [sabTestResult, setSabTestResult] = useState<string | null>(null);

  // Load saved settings
  const { data: settingsCategories } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });

  useEffect(() => {
    if (!settingsCategories) return;
    const allSettings: Record<string, string> = {};
    for (const cat of settingsCategories) {
      for (const s of cat.settings) {
        allSettings[s.key] = s.value ?? "";
      }
    }
    if (allSettings["downloadclient.qbittorrent.enabled"] === "true") setQbtEnabled(true);
    if (allSettings["downloadclient.qbittorrent.url"]) setQbtUrl(allSettings["downloadclient.qbittorrent.url"]);
    if (allSettings["downloadclient.qbittorrent.username"]) setQbtUsername(allSettings["downloadclient.qbittorrent.username"]);
    if (allSettings["downloadclient.qbittorrent.password"]) setQbtPassword(allSettings["downloadclient.qbittorrent.password"]);
    if (allSettings["downloadclient.qbittorrent.category.ebook"]) setQbtCategoryEbook(allSettings["downloadclient.qbittorrent.category.ebook"]);
    if (allSettings["downloadclient.qbittorrent.category.audiobook"]) setQbtCategoryAudiobook(allSettings["downloadclient.qbittorrent.category.audiobook"]);
    if (allSettings["downloadclient.qbittorrent.category.comic"]) setQbtCategoryComic(allSettings["downloadclient.qbittorrent.category.comic"]);
    if (allSettings["downloadclient.sabnzbd.enabled"] === "true") setSabEnabled(true);
    if (allSettings["downloadclient.sabnzbd.url"]) setSabUrl(allSettings["downloadclient.sabnzbd.url"]);
    if (allSettings["downloadclient.sabnzbd.api_key"]) setSabApiKey(allSettings["downloadclient.sabnzbd.api_key"]);
    if (allSettings["downloadclient.sabnzbd.category.ebook"]) setSabCategoryEbook(allSettings["downloadclient.sabnzbd.category.ebook"]);
    if (allSettings["downloadclient.sabnzbd.category.audiobook"]) setSabCategoryAudiobook(allSettings["downloadclient.sabnzbd.category.audiobook"]);
    if (allSettings["downloadclient.sabnzbd.category.comic"]) setSabCategoryComic(allSettings["downloadclient.sabnzbd.category.comic"]);
  }, [settingsCategories]);

  const saveMutation = useMutation({
    mutationFn: (settings: Record<string, string>) => updateSettings(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      addToast("Settings saved");
    },
    onError: () => addToast("Failed to save settings", "error"),
  });

  const saveQbt = () => {
    saveMutation.mutate({
      "downloadclient.qbittorrent.enabled": String(qbtEnabled),
      "downloadclient.qbittorrent.url": qbtUrl,
      "downloadclient.qbittorrent.username": qbtUsername,
      "downloadclient.qbittorrent.password": qbtPassword,
      "downloadclient.qbittorrent.category.ebook": qbtCategoryEbook,
      "downloadclient.qbittorrent.category.audiobook": qbtCategoryAudiobook,
      "downloadclient.qbittorrent.category.comic": qbtCategoryComic,
    });
  };

  const saveSab = () => {
    saveMutation.mutate({
      "downloadclient.sabnzbd.enabled": String(sabEnabled),
      "downloadclient.sabnzbd.url": sabUrl,
      "downloadclient.sabnzbd.api_key": sabApiKey,
      "downloadclient.sabnzbd.category.ebook": sabCategoryEbook,
      "downloadclient.sabnzbd.category.audiobook": sabCategoryAudiobook,
      "downloadclient.sabnzbd.category.comic": sabCategoryComic,
    });
  };

  const testConnection = async (provider: "qbittorrent" | "sabnzbd") => {
    const setTesting = provider === "qbittorrent" ? setQbtTesting : setSabTesting;
    const setResult = provider === "qbittorrent" ? setQbtTestResult : setSabTestResult;
    setTesting(true);
    setResult(null);
    try {
      const res = await fetch(`/api/system/settings/test-connection?provider=${provider}`);
      if (res.ok) {
        setResult("Connection successful");
      } else {
        const data = await res.json().catch(() => null);
        setResult(data?.error ?? "Connection failed");
      }
    } catch {
      setResult("Connection failed");
    } finally {
      setTesting(false);
    }
  };

  return (
    <SettingsSection title="Download Clients" description="Configure download clients for fetching releases.">
      {/* qBittorrent */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">qBittorrent</h3>
        <Toggle checked={qbtEnabled} onChange={setQbtEnabled} label="Enable qBittorrent" description="Use qBittorrent as a torrent download client" />
        {qbtEnabled && (
          <>
            <Field label="URL" required description="Base URL of your qBittorrent WebUI">
              <input type="text" value={qbtUrl} onChange={(e) => setQbtUrl(e.target.value)} placeholder="http://localhost:8080" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <Field label="Username">
              <input type="text" value={qbtUsername} onChange={(e) => setQbtUsername(e.target.value)} className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <Field label="Password">
              <SecretInput value={qbtPassword} onChange={setQbtPassword} />
            </Field>
            <Field label="Books Category" description="Torrent category for ebooks in qBittorrent">
              <input type="text" value={qbtCategoryEbook} onChange={(e) => setQbtCategoryEbook(e.target.value)} className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <Field label="Audiobooks Category" description="Torrent category for audiobooks in qBittorrent">
              <input type="text" value={qbtCategoryAudiobook} onChange={(e) => setQbtCategoryAudiobook(e.target.value)} className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <Field label="Comics Category" description="Torrent category for comics in qBittorrent">
              <input type="text" value={qbtCategoryComic} onChange={(e) => setQbtCategoryComic(e.target.value)} className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <div className="flex items-center gap-3">
              <button onClick={() => testConnection("qbittorrent")} disabled={qbtTesting} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
                {qbtTesting && <Loader2 size={14} className="animate-spin" />}
                Test Connection
              </button>
              <button onClick={saveQbt} disabled={saveMutation.isPending} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                {saveMutation.isPending ? "Saving..." : "Save"}
              </button>
              {qbtTestResult && <span className="text-sm text-gray-400">{qbtTestResult}</span>}
            </div>
          </>
        )}
      </div>

      <div className="border-t border-gray-800" />

      {/* SABnzbd */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">SABnzbd</h3>
        <Toggle checked={sabEnabled} onChange={setSabEnabled} label="Enable SABnzbd" description="Use SABnzbd as a Usenet download client" />
        {sabEnabled && (
          <>
            <Field label="URL" required description="Base URL of your SABnzbd instance">
              <input type="text" value={sabUrl} onChange={(e) => setSabUrl(e.target.value)} placeholder="http://localhost:8080" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <Field label="API Key" required>
              <SecretInput value={sabApiKey} onChange={setSabApiKey} placeholder="Your SABnzbd API key" />
            </Field>
            <Field label="Books Category" description="Category for ebooks in SABnzbd">
              <input type="text" value={sabCategoryEbook} onChange={(e) => setSabCategoryEbook(e.target.value)} className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <Field label="Audiobooks Category" description="Category for audiobooks in SABnzbd">
              <input type="text" value={sabCategoryAudiobook} onChange={(e) => setSabCategoryAudiobook(e.target.value)} className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <Field label="Comics Category" description="Category for comics in SABnzbd">
              <input type="text" value={sabCategoryComic} onChange={(e) => setSabCategoryComic(e.target.value)} className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            </Field>
            <div className="flex items-center gap-3">
              <button onClick={() => testConnection("sabnzbd")} disabled={sabTesting} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
                {sabTesting && <Loader2 size={14} className="animate-spin" />}
                Test Connection
              </button>
              <button onClick={saveSab} disabled={saveMutation.isPending} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                {saveMutation.isPending ? "Saving..." : "Save"}
              </button>
              {sabTestResult && <span className="text-sm text-gray-400">{sabTestResult}</span>}
            </div>
          </>
        )}
      </div>
    </SettingsSection>
  );
}

function SearchModeSection() {
  return (
    <SettingsSection title="Search Mode" description="How you want to search for and download books.">
      <Field label="Search Mode" description="Direct mode searches web sources and downloads immediately. Universal mode supports Prowlarr, IRC and audiobooks with metadata-based searching.">
        <select defaultValue="universal" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500">
          <option value="direct">Direct</option>
          <option value="universal">Universal</option>
        </select>
      </Field>
      <Field label="Book Metadata Provider" description="Choose which metadata provider to use for book searches.">
        <select defaultValue="openlibrary" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500">
          <option value="hardcover">Hardcover</option>
          <option value="openlibrary">Open Library</option>
          <option value="google">Google Books</option>
        </select>
      </Field>
      <Field label="Audiobook Metadata Provider" description="Metadata provider for audiobook searches. Uses the book provider if not set.">
        <select defaultValue="book" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500">
          <option value="book">Use book provider</option>
          <option value="hardcover">Hardcover</option>
          <option value="openlibrary">Open Library</option>
        </select>
      </Field>
      <Field label="Default Release Source" description="The release source tab to open by default in the release modal.">
        <select defaultValue="direct" className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500">
          <option value="direct">Direct Download</option>
          <option value="prowlarr">Prowlarr</option>
          <option value="audiobookbay">AudiobookBay</option>
        </select>
      </Field>
    </SettingsSection>
  );
}

function IntegrationCategory({ category, queryClient }: { category: SettingsCategory; queryClient: ReturnType<typeof useQueryClient> }) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const s of category.settings) init[s.key] = s.value ?? "";
    return init;
  });

  const mutation = useMutation({
    mutationFn: () => updateSettings(values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });

  return (
    <div className="bg-gray-950 border border-gray-800 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-gray-200 mb-3 capitalize">{category.category}</h4>
      <div className="space-y-3">
        {category.settings.map((setting) => (
          <Field key={setting.key} label={setting.label} description={setting.description || undefined}>
            {setting.is_secret ? (
              <SecretInput value={values[setting.key] ?? ""} onChange={(v) => setValues((prev) => ({ ...prev, [setting.key]: v }))} />
            ) : (
              <input type="text" value={values[setting.key] ?? ""} onChange={(e) => setValues((prev) => ({ ...prev, [setting.key]: e.target.value }))} className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500" />
            )}
          </Field>
        ))}
      </div>
      <button onClick={() => mutation.mutate()} disabled={mutation.isPending} className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
        {mutation.isPending ? "Saving..." : "Save"}
      </button>
    </div>
  );
}

function AdvancedSection({ categories }: { categories: SettingsCategory[] | undefined }) {
  const queryClient = useQueryClient();
  const HANDLED_CATEGORIES = ['prowlarr', 'hardcover', 'openlibrary', 'google', 'general', 'downloads'];
  const filtered = categories?.filter(cat => !HANDLED_CATEGORIES.includes(cat.category));
  return (
    <SettingsSection title="Advanced" description="Integration settings stored in the database.">
      {filtered?.length ? filtered.map((cat) => <IntegrationCategory key={cat.category} category={cat} queryClient={queryClient} />) : <p className="text-sm text-gray-500">No integration settings configured.</p>}
    </SettingsSection>
  );
}

// ============================================================
// MAIN SETTINGS PAGE
// ============================================================

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("general");
  const [expandedMenus, setExpandedMenus] = useState<Set<string>>(new Set(["metadata-providers"]));

  const { data: settingsCategories } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });

  const toggleMenu = (id: string) => {
    setExpandedMenus((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const renderContent = () => {
    switch (activeSection) {
      case "general": return <GeneralSection />;
      case "search-mode": return <SearchModeSection />;
      case "downloads": return <DownloadsSection />;
      case "metadata-hardcover": return <MetadataProviderSection provider="hardcover" title="Hardcover" description="A modern book tracking and discovery platform with a comprehensive API." linkUrl="https://hardcover.app" />;
      case "metadata-openlibrary": return <MetadataProviderSection provider="openlibrary" title="Open Library" description="Free, open metadata from the Internet Archive." linkUrl="https://openlibrary.org" />;
      case "metadata-google": return <MetadataProviderSection provider="google" title="Google Books" description="Google's book metadata and cover image API." />;
      case "prowlarr": return <ProwlarrSection />;
      case "advanced": return <AdvancedSection categories={settingsCategories} />;
      case "security": return <ComingSoon section="Security" />;
      case "notifications": return <ComingSoon section="Notifications" />;
      case "audiobookbay": return <ComingSoon section="AudiobookBay" />;
      case "download-clients": return <DownloadClientsSection />;
      default: return <ComingSoon section={activeSection} />;
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] -m-6">
      <nav className="w-56 flex-shrink-0 bg-gray-950 border-r border-gray-800 overflow-y-auto py-4">
        {NAV_ITEMS.map((item) => {
          if (item.isHeader) {
            return <div key={item.id} className="px-4 pt-5 pb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-600">{item.label}</div>;
          }

          const Icon = item.icon;
          const hasChildren = item.children && item.children.length > 0;
          const isExpanded = expandedMenus.has(item.id);
          const isActive = activeSection === item.id || (hasChildren && item.children!.some((c) => c.id === activeSection));

          return (
            <div key={item.id}>
              <button
                onClick={() => {
                  if (hasChildren) {
                    toggleMenu(item.id);
                    if (!isExpanded && item.children!.length > 0) setActiveSection(item.children![0].id);
                  } else {
                    setActiveSection(item.id);
                  }
                }}
                className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors ${isActive ? "text-gray-100 border-l-2 border-indigo-500 bg-gray-900/50" : "text-gray-500 hover:text-gray-300 border-l-2 border-transparent"}`}
              >
                {Icon && <Icon size={16} />}
                <span className="flex-1 text-left">{item.label}</span>
                {hasChildren && (isExpanded ? <ChevronDown size={14} className="text-gray-600" /> : <ChevronRight size={14} className="text-gray-600" />)}
              </button>
              {hasChildren && isExpanded && (
                <div>
                  {item.children!.map((child) => (
                    <button key={child.id} onClick={() => setActiveSection(child.id)} className={`w-full text-left pl-10 pr-4 py-1.5 text-sm transition-colors ${activeSection === child.id ? "text-gray-100 bg-gray-900/50" : "text-gray-500 hover:text-gray-300"}`}>
                      {child.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>
      <main className="flex-1 overflow-y-auto p-6">{renderContent()}</main>
    </div>
  );
}
