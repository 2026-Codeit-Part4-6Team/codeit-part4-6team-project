import { type ReactNode, useState } from "react";

import type { AppRoute } from "../appState";
import type { UserResponse } from "../api";
import { Sidebar } from "./Sidebar";

type DashboardLayoutProps = {
  user: UserResponse;
  route: AppRoute;
  onNavigate: (route: AppRoute) => void;
  onLogout: () => void;
  children: ReactNode;
};

export function DashboardLayout({
  user,
  route,
  onNavigate,
  onLogout,
  children,
}: DashboardLayoutProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="dashboard-shell">
      <button
        type="button"
        className="mobile-menu-button"
        aria-label="메뉴 열기"
        aria-controls="app-sidebar"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen(true)}
      >
        <img src="/assets/menu.svg" alt="" />
      </button>
      <Sidebar
        user={user}
        route={route}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onNavigate={onNavigate}
        onLogout={onLogout}
      />
      {menuOpen && <button type="button" className="sidebar-backdrop" aria-label="메뉴 닫기" onClick={() => setMenuOpen(false)} />}
      <main className="dashboard-content">{children}</main>
    </div>
  );
}
