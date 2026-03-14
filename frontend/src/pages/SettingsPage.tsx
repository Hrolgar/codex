import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getLibraries,
  createLibrary,
  deleteLibrary,
  scanLibrary,
  getSystemStats,
  getSettings,
  updateSettings,
  type SettingsCategory,
} from "@/api/client";
import { Plus, Trash2, RefreshCw, FolderOpen, Save } from "lucide-react";

function CategoryCard({ category }: { category: SettingsCategory }) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const s of category.settings) {
      init[s.key] = s.value ?? "";
    }
    return init;
  });
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const mutation = useMutation({
    mutationFn: () => updateSettings(values),
    onSuccess: () => {
      setToast({ type: "success", msg: "Settings saved" });
      setTimeout(() => setToast(null), 3000);
    },
    onError: (err: Error) => {
      setToast({ type: "error", msg: err.message });
      setTimeout(() => setToast(null), 5000);
    },
  });

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
      <h4 className="text-md font-semibold text-gray-100 capitalize mb-4">
        {category.category}
      </h4>
      <div className="space-y-3">
        {category.settings.map((setting) => (
          <div key={setting.key}>
            <label className="block text-xs text-gray-500 mb-1">
              {setting.label}
            </label>
            {setting.description && (
              <p className="text-xs text-gray-600 mb-1">{setting.description}</p>
            )}
            <input
              type={setting.is_secret ? "password" : "text"}
              value={values[setting.key] ?? ""}
              onChange={(e) =>
                setValues((prev) => ({ ...prev, [setting.key]: e.target.value }))
              }
              className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3 mt-4">
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          <Save size={14} />
          Save
        </button>
        {toast && (
          <span
            className={`text-sm ${toast.type === "success" ? "text-green-400" : "text-red-400"}`}
          >
            {toast.msg}
          </span>
        )}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [scannerType, setScannerType] = useState("ebook");
  const [configJson, setConfigJson] = useState('{"path": ""}');

  const { data: libraries } = useQuery({
    queryKey: ["libraries"],
    queryFn: getLibraries,
  });

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: getSystemStats,
  });

  const { data: settingsCategories } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });

  const addMutation = useMutation({
    mutationFn: createLibrary,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      setName("");
      setConfigJson('{"path": ""}');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteLibrary,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["libraries"] }),
  });

  const scanMutation = useMutation({ mutationFn: scanLibrary });

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    try {
      const config = JSON.parse(configJson);
      addMutation.mutate({ name, scanner_type: scannerType, config });
    } catch {
      alert("Invalid JSON in config field");
    }
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <h2 className="text-2xl font-bold text-gray-100">Settings</h2>

      {/* System Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { label: "Libraries", value: stats.libraries },
            { label: "Books", value: stats.books },
            { label: "Library Items", value: stats.library_items },
          ].map((s) => (
            <div
              key={s.label}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4"
            >
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className="text-2xl font-bold text-gray-100 mt-1">
                {s.value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Libraries */}
      <div>
        <h3 className="text-lg font-semibold text-gray-200 mb-3">Libraries</h3>
        <div className="space-y-2">
          {libraries?.map((lib) => (
            <div
              key={lib.id}
              className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center gap-3">
                <FolderOpen size={18} className="text-indigo-400" />
                <div>
                  <p className="text-sm font-medium text-gray-100">
                    {lib.name}
                  </p>
                  <p className="text-xs text-gray-500">{lib.scanner_type}</p>
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
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Scanner Type
            </label>
            <select
              value={scannerType}
              onChange={(e) => setScannerType(e.target.value)}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="ebook">eBook</option>
              <option value="audiobook">Audiobook</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">
            Config (JSON)
          </label>
          <textarea
            value={configJson}
            onChange={(e) => setConfigJson(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 font-mono focus:outline-none focus:border-indigo-500"
          />
        </div>
        <button
          type="submit"
          disabled={addMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          <Plus size={16} />
          Add Library
        </button>
      </form>

      {/* Integrations */}
      {settingsCategories && settingsCategories.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-200 mb-3">
            Integrations
          </h3>
          <div className="space-y-4">
            {settingsCategories.map((cat) => (
              <CategoryCard key={cat.category} category={cat} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
