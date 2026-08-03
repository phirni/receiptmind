import React from "react";
import { NavLink } from "react-router-dom";
import { Receipt, Upload, Search, BarChart3, LayoutList } from "lucide-react";
import clsx from "clsx";

const links = [
  { to: "/", label: "Upload", icon: Upload },
  { to: "/receipts", label: "Receipts", icon: LayoutList },
  { to: "/search", label: "Search", icon: Search },
  { to: "/statistics", label: "Statistics", icon: BarChart3 },
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-ink/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-teal-dim text-amber">
            <Receipt size={18} strokeWidth={2.25} />
          </div>
          <span className="font-display text-lg font-semibold tracking-tight text-ash-100">
            Receipt<span className="text-amber">Mind</span>
          </span>
        </div>

        <nav className="flex items-center gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                clsx(
                  "focus-ring flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                  isActive ? "bg-raised text-amber" : "text-ash-500 hover:text-ash-100"
                )
              }
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
