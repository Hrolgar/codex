import { ReactNode, useState } from "react";
import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getNotifications } from "@/api/client";
import { User, BookOpen as BookIcon, Search, Download, Star, Settings, Menu, X, BookOpen, Bell, Layers } from "lucide-react";

const navItems = [
  { to: "/", icon: User, label: "Authors" },
  { to: "/books", icon: BookIcon, label: "Library" },
  { to: "/books?media_type=comic", icon: Layers, label: "Comics" },
  { to: "/search", icon: Search, label: "Search" },
  { to: "/downloads", icon: Download, label: "Downloads" },
  { to: "/wishlist", icon: Star, label: "Wishlist" },
  { to: "/notifications", icon: Bell, label: "Notifications" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { data: notifications } = useQuery({
    queryKey: ["notifications"],
    queryFn: getNotifications,
    refetchInterval: 30_000,
  });
  const unreadCount = notifications?.filter((n) => !n.read).length ?? 0;

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-60 flex-shrink-0 border-r border-gray-800 bg-gray-950 flex flex-col transform transition-transform md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="h-14 px-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <BookOpen size={22} className="text-indigo-400" />
            <h1 className="text-lg font-bold text-gray-100 tracking-tight">Codex</h1>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1 text-gray-400 hover:text-gray-200"
          >
            <X size={20} />
          </button>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/" || to === "/books"}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/20"
                    : "text-gray-400 hover:bg-gray-800/60 hover:text-gray-200"
                }`
              }
            >
              <Icon size={18} />
              {label}
              {label === "Notifications" && unreadCount > 0 && (
                <span className="ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-red-500 text-white min-w-[18px] text-center">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-800">
          <p className="text-[11px] text-gray-600">Codex v0.1.0</p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <header className="h-14 md:hidden flex items-center px-4 border-b border-gray-800 bg-gray-950">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-1 text-gray-400 hover:text-gray-200"
          >
            <Menu size={22} />
          </button>
          <div className="flex items-center gap-2 ml-3">
            <BookOpen size={18} className="text-indigo-400" />
            <span className="font-semibold text-gray-100">Codex</span>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
