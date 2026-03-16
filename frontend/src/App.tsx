import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import AuthorsPage from "./pages/AuthorsPage";
import DashboardPage from "./pages/DashboardPage";
import AuthorDetailPage from "./pages/AuthorDetailPage";
import SeriesPage from "./pages/SeriesPage";
import SeriesDetailPage from "./pages/SeriesDetailPage";
import LibraryPage from "./pages/LibraryPage";
import BookDetailPage from "./pages/BookDetailPage";
import SearchPage from "./pages/SearchPage";
import DownloadsPage from "./pages/DownloadsPage";
import WishlistPage from "./pages/WishlistPage";
import NotificationsPage from "./pages/NotificationsPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/authors" element={<AuthorsPage />} />
        <Route path="/authors/:id" element={<AuthorDetailPage />} />
        <Route path="/series" element={<SeriesPage />} />
        <Route path="/series/:id" element={<SeriesDetailPage />} />
        <Route path="/books" element={<LibraryPage />} />
        <Route path="/comics" element={<LibraryPage initialMediaType="comic" title="Comics" />} />
        <Route path="/books/:id" element={<BookDetailPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/downloads" element={<DownloadsPage />} />
        <Route path="/wishlist" element={<WishlistPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </AppLayout>
  );
}
