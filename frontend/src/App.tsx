import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import LibraryPage from "./pages/LibraryPage";
import SearchPage from "./pages/SearchPage";
import DownloadsPage from "./pages/DownloadsPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<LibraryPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/downloads" element={<DownloadsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </AppLayout>
  );
}
