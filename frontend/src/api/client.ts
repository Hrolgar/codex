const BASE_URL = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }
  return res.json();
}

// Types
export interface AuthorListItem {
  id: string;
  name: string;
  sort_name: string | null;
  book_count: number;
  owned_count: number;
  monitored: boolean;
  photo_url: string | null;
  catalog_status: string;
}

export interface AuthorDetail {
  id: string;
  name: string;
  sort_name: string | null;
  monitored: boolean;
  openlibrary_key: string | null;
  bio: string | null;
  photo_url: string | null;
  catalog_status: string;
  series: { id: string; name: string; book_count: number; owned_count: number }[];
  standalone_books: (BookListItem & { owned: boolean })[];
}

export interface SeriesListItem {
  id: string;
  name: string;
  book_count: number;
  author_names: string | null;
}

export interface SeriesDetail {
  id: string;
  name: string;
  books: (BookListItem & { position: number })[];
  authors: { id: string; name: string }[];
}

export interface BookListItem {
  id: string;
  title: string;
  author: string | null;
  media_type: string;
  cover_url: string | null;
  isbn_13: string | null;
  publish_year: number | null;
  owned?: boolean;
  reading_status?: string | null;
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
  reading_status: string | null;
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
  id: string;
  name: string;
  scanner_type: string;
  scan_status: string;
  last_scan_at: string | null;
  created_at: string;
  updated_at: string;
  path: string | null;
  url: string | null;
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

export function getAuthors(search?: string) {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  return request<{ items: AuthorListItem[]; total: number }>(`/authors?${query}`).then(
    (res) => res.items
  );
}

export function getAuthor(id: string) {
  return request<AuthorDetail>(`/authors/${id}`);
}

export function addAuthor(name: string) {
  return request<{ id: string }>("/authors", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function refreshAuthor(id: string) {
  return request<{ status: string }>(`/authors/${id}/refresh`, {
    method: "POST",
  });
}

export function deleteAuthor(id: string, removeBooks?: boolean) {
  const query = removeBooks ? "?remove_books=true" : "";
  return request<void>(`/authors/${id}${query}`, { method: "DELETE" });
}

export function getSeries(search?: string) {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  return request<SeriesListItem[]>(`/series?${query}`);
}

export function getSeriesDetail(id: string) {
  return request<SeriesDetail>(`/series/${id}`);
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
  path?: string;
  url?: string;
  api_key?: string;
}) {
  return request<Library>("/libraries", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteLibrary(id: string) {
  return request<void>(`/libraries/${id}`, { method: "DELETE" });
}

export function scanLibrary(id: string) {
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

// Search & Download types
export interface SearchResult {
  book_id: string | null;
  title: string;
  author: string | null;
  isbn: string | null;
  cover_url: string | null;
  source: string | null;
  owned: boolean;
  match_confidence: number;
  download_url: string | null;
  indexer: string | null;
  size: number | null;
  seeders: number | null;
  format: string | null;
}

export interface DownloadResponse {
  id: string;
  book_id: string | null;
  source_type: string;
  source_url: string;
  status: string;
  progress: number;
  error: string | null;
  target_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface DownloadCreate {
  source_url: string;
  source_type: string;
  book_id?: string;
  filename?: string;
}

// Search & Download functions
export function searchExternal(q: string, mediaType?: string) {
  const query = new URLSearchParams({ q });
  if (mediaType) query.set("media_type", mediaType);
  return request<SearchResult[]>(`/search?${query}`);
}

export function getDownloads(status?: string) {
  const query = new URLSearchParams();
  if (status) query.set("status", status);
  return request<DownloadResponse[]>(`/downloads?${query}`);
}

export function createDownload(body: DownloadCreate) {
  return request<DownloadResponse>("/downloads", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteDownload(id: string) {
  return request<void>(`/downloads/${id}`, { method: "DELETE" });
}

export function retryDownload(id: string) {
  return request<DownloadResponse>(`/downloads/${id}/retry`, {
    method: "POST",
  });
}

export function seedDemoData() {
  return request<{ status: string }>("/dev/seed", { method: "POST" });
}

export function clearDemoData() {
  return request<{ status: string }>("/dev/clear", { method: "POST" });
}

// Wishlist types & functions
export interface WishlistItem {
  id: string;
  book_id: string | null;
  search_title: string | null;
  search_author: string | null;
  status: "waiting" | "found" | "downloading" | "complete";
  auto_download: boolean;
  created_at: string;
  updated_at: string;
}

export interface WishlistCreate {
  book_id?: string;
  search_title: string;
  search_author?: string;
  auto_download?: boolean;
}

export function getWishlist() {
  return request<WishlistItem[]>("/wishlist");
}

export function addToWishlist(data: WishlistCreate) {
  return request<WishlistItem>("/wishlist", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function removeFromWishlist(id: string) {
  return request<void>(`/wishlist/${id}`, { method: "DELETE" });
}

export function updateWishlistItem(id: string, data: Partial<WishlistCreate & { status: string }>) {
  return request<WishlistItem>(`/wishlist/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// Notifications
export interface Notification {
  id: string;
  title: string;
  message: string;
  notification_type: "info" | "success" | "warning" | "error";
  read: boolean;
  created_at: string;
}

export function getNotifications() {
  return request<Notification[]>("/notifications");
}

export function markNotificationRead(id: string) {
  return request<void>(`/notifications/${id}/read`, { method: "POST" });
}

// Reading status
export type ReadingStatus = "unread" | "reading" | "read";

export function updateBookStatus(id: string, status: ReadingStatus) {
  return request<{ status: string }>(`/books/${id}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}
