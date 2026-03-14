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
export interface BookListItem {
  id: string;
  title: string;
  author: string | null;
  media_type: string;
  cover_url: string | null;
  isbn_13: string | null;
  publish_year: number | null;
}

export interface AuthorBrief {
  id: string;
  name: string;
  role: string;
}

export interface SeriesBrief {
  id: string;
  name: string;
  position: number;
}

export interface LibraryItemBrief {
  id: string;
  library_id: string;
  file_path: string;
  file_format: string | null;
  file_size: number | null;
}

export interface BookDetail {
  id: string;
  title: string;
  subtitle: string | null;
  description: string | null;
  cover_url: string | null;
  media_type: string;
  language: string | null;
  publish_year: number | null;
  page_count: number | null;
  duration_seconds: number | null;
  isbn_10: string | null;
  isbn_13: string | null;
  asin: string | null;
  openlibrary_key: string | null;
  metadata_source: string | null;
  authors: AuthorBrief[];
  series: SeriesBrief[];
  library_items: LibraryItemBrief[];
  created_at: string;
  updated_at: string;
}

export interface BooksResponse {
  items: BookListItem[];
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

export function getBook(id: string) {
  return request<BookDetail>(`/books/${id}`);
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
