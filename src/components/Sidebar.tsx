/**
 * Sidebar — navigation with icons and health indicator.
 */

import { NavLink } from "react-router-dom";
import {
  Home,
  FolderInput,
  MessageSquare,
  Database,
  Settings,
} from "lucide-react";
import HealthIndicator from "./HealthIndicator";

const navItems = [
  { to: "/", icon: Home, label: "Home" },
  { to: "/index", icon: FolderInput, label: "Index" },
  { to: "/context", icon: MessageSquare, label: "Context" },
  { to: "/memory", icon: Database, label: "Memory" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  return (
    <aside className="flex flex-col w-16 bg-gray-900 dark:bg-gray-950 text-gray-300">
      {/* Logo area */}
      <div className="flex items-center justify-center h-14 border-b border-gray-700">
        <span className="text-lg font-bold text-white">A</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center justify-center h-12 transition-colors ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "hover:bg-gray-800 text-gray-400 hover:text-white"
              }`
            }
            title={item.label}
          >
            <item.icon size={20} />
          </NavLink>
        ))}
      </nav>

      {/* Health indicator at bottom */}
      <div className="py-4 border-t border-gray-700">
        <HealthIndicator />
      </div>
    </aside>
  );
}
