const BASE_URL = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Types
export interface Book {
  id: number;
  title: string;
  author: string;
  media_type: "ebook" | "audiobook";
  cover_path?: string;
  file_path: string;
  library_id: number;
  metadata?: Record<string, unknown>;
}

export interface BooksResponse {
  items: Book[];
  total: number;
  page: number;
  per_page: number;
}

export interface Library {
  id: number;
  name: string;
  scanner_type: string;
  config: Record<string, unknown>;
}

export interface SystemStats {
  books: number;
  libraries: number;
  library_items: number;
}

export interface SettingItem {
  key: string;
  label: string;
  description: string;
  is_secret: boolean;
  value: string;
}

export interface SettingsCategory {
  category: string;
  settings: SettingItem[];
}

// API functions
export function getHealth() {
  return request<{ status: string }>("/health");
}

export function getBooks(params: {
  search?: string;
  media_type?: string;
  page?: number;
  per_page?: number;
}) {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.media_type) query.set("media_type", params.media_type);
  if (params.page) query.set("page", String(params.page));
  if (params.per_page) query.set("per_page", String(params.per_page));
  return request<BooksResponse>(`/books?${query}`);
}

export function getBook(id: number) {
  return request<Book>(`/books/${id}`);
}

export function getLibraries() {
  return request<Library[]>("/libraries");
}

export function createLibrary(body: {
  name: string;
  scanner_type: string;
  config: Record<string, unknown>;
}) {
  return request<Library>("/libraries", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteLibrary(id: number) {
  return request<void>(`/libraries/${id}`, { method: "DELETE" });
}

export function scanLibrary(id: number) {
  return request<{ status: string }>(`/libraries/${id}/scan`, {
    method: "POST",
  });
}

export function getSystemStats() {
  return request<SystemStats>("/system/stats");
}

export function getSettings() {
  return request<SettingsCategory[]>("/system/settings");
}

export function updateSettings(settings: Record<string, string>) {
  return request<void>("/system/settings", {
    method: "PUT",
    body: JSON.stringify({ settings }),
  });
}

export function seedDemoData() {
  return request<{ status: string }>("/dev/seed", { method: "POST" });
}

export function clearDemoData() {
  return request<{ status: string }>("/dev/clear", { method: "POST" });
}
