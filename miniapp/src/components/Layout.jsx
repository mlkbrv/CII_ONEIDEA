/*
 * The frame every screen sits in: a header with the coin balance, the bottom
 * navigation, and Telegram's back button on anything that is not a root tab.
 */
import { useEffect } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

import { useCoins, useUnreadCount } from "../api/queries";
import { useT } from "../i18n";
import { backButton } from "../platform/telegram";
import { Coins } from "./ui";

// The five root destinations. Anything else is a detail screen and gets a
// back button instead of a highlighted tab.
const TABS = [
  { to: "/", key: "nav.home", icon: "🏠" },
  { to: "/shop", key: "nav.shop", icon: "🛍" },
  { to: "/battles", key: "nav.battles", icon: "⚔️" },
  { to: "/friends", key: "nav.friends", icon: "👥" },
  { to: "/profile", key: "nav.profile", icon: "🐻‍❄️" },
];

const ROOTS = TABS.map((tab) => tab.to);

export default function Layout({ children }) {
  const t = useT();
  const location = useLocation();
  const navigate = useNavigate();
  const { data: coins } = useCoins();
  const { data: unread } = useUnreadCount();

  const isRoot = ROOTS.includes(location.pathname);

  useEffect(() => {
    // Telegram's own back button, not a drawn one: it is where users already
    // look, and it sits in the client's chrome rather than costing us a row
    // of screen. Nothing happens outside Telegram.
    if (isRoot) return undefined;
    return backButton(() => navigate(-1));
  }, [isRoot, navigate]);

  return (
    <div className="app">
      <header className="header">
        <NavLink to="/" className="brand">
          <span aria-hidden="true">🐻‍❄️</span> Cola Fest
        </NavLink>
        <div className="header-right">
          <NavLink to="/notifications" className="bell" aria-label={t("nav.notifications")}>
            🔔
            {unread?.unread ? <span className="badge">{unread.unread}</span> : null}
          </NavLink>
          <Coins amount={coins?.balance} className="header-coins" />
        </div>
      </header>

      <main className="content">{children}</main>

      <nav className="nav">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === "/"}
            className={({ isActive }) => `nav-item ${isActive ? "is-active" : ""}`}
          >
            <span className="nav-icon" aria-hidden="true">
              {tab.icon}
            </span>
            <span className="nav-label">{t(tab.key)}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
