import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import AuthorsPage from "./pages/AuthorsPage";
import AuthorDetailPage from "./pages/AuthorDetailPage";
import SeriesDetailPage from "./pages/SeriesDetailPage";
import LibraryPage from "./pages/LibraryPage";
import BookDetailPage from "./pages/BookDetailPage";
import SearchPage from "./pages/SearchPage";
import DownloadsPage from "./pages/DownloadsPage";
import WishlistPage from "./pages/WishlistPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<AuthorsPage />} />
        <Route path="/authors/:id" element={<AuthorDetailPage />} />
        <Route path="/series/:id" element={<SeriesDetailPage />} />
        <Route path="/books" element={<LibraryPage />} />
        <Route path="/books/:id" element={<BookDetailPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/downloads" element={<DownloadsPage />} />
        <Route path="/wishlist" element={<WishlistPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </AppLayout>
  );
}
