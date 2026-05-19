"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Bell, Search, Settings, LogOut, User as UserIcon,
  Activity, ShieldCheck, FileText, CheckCircle, AlertTriangle, XCircle,
  ExternalLink,
} from "lucide-react";
import type { Notification } from "@/lib/api";
import { fetchNotifications } from "@/lib/api";

const PAGE_TITLES: Record<string, { title: string; desc: string }> = {
  "/": { title: "Dashboard", desc: "Infrastructure overview at a glance" },
  "/deploy": { title: "Deploy Wizard", desc: "Configure and launch infrastructure" },
  "/policies": { title: "Policy Dashboard", desc: "Security and governance rules" },
  "/audit": { title: "Audit Log", desc: "Deployment history and events" },
  "/team": { title: "Team Management", desc: "Users, roles, and permissions" },
  "/drift": { title: "Drift Detection", desc: "Infrastructure state monitoring" },
  "/terminal": { title: "CloudShell", desc: "Browser-based terminal" },
  "/settings": { title: "Settings", desc: "Admin configuration" },
};

const NOTIFICATION_ICONS: Record<string, typeof Bell> = {
  approval: CheckCircle,
  drift: Activity,
  audit: FileText,
  policy: ShieldCheck,
};

const SEVERITY_COLORS: Record<string, string> = {
  info: "var(--accent-blue)",
  warning: "var(--accent-amber)",
  error: "var(--accent-red)",
  success: "var(--accent-green)",
};

export default function TopBar() {
  const pathname = usePathname();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [user, setUser] = useState<{ name?: string; username?: string; role?: string } | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notifCount, setNotifCount] = useState(0);

  useEffect(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem("auth_user") || "{}");
      if (stored.username) setUser(stored);
    } catch {}
  }, [pathname]);

  // Fetch live notifications
  const loadNotifications = useCallback(() => {
    fetchNotifications()
      .then((data) => {
        setNotifications(data.notifications);
        setNotifCount(data.unread);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, [loadNotifications]);

  if (pathname === "/login") return null;

  const page = PAGE_TITLES[pathname] ?? { title: "Dashboard", desc: "" };

  const searchResults = Object.entries(PAGE_TITLES)
    .filter(([, data]) => 
      data.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
      data.desc.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .map(([path, data]) => ({ path, ...data }));

  const handleSearch = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && searchQuery.trim()) {
      if (searchResults.length > 0) {
        router.push(searchResults[0].path);
      } else {
        router.push(`/audit?actor=${encodeURIComponent(searchQuery)}`);
      }
      setSearchQuery("");
      setShowSearchDropdown(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem("auth_user");
    router.push("/login");
  };

  const handleNotificationClick = (n: Notification) => {
    router.push(n.action_url);
    setShowNotifications(false);
  };

  const formatTime = (ts: string) => {
    if (!ts) return "";
    try {
      const d = new Date(ts);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return "just now";
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}h ago`;
      return d.toLocaleDateString();
    } catch { return ""; }
  };

  return (
    <header
      style={{
        height: "var(--topbar-height)",
        background: "rgba(6, 6, 11, 0.85)",
        borderBottom: "1px solid var(--border-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 36px",
        position: "sticky",
        top: 0,
        zIndex: 40,
        backdropFilter: "blur(20px) saturate(1.3)",
        WebkitBackdropFilter: "blur(20px) saturate(1.3)",
      }}
    >
      <div>
        <h2 style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
          {page.title}
        </h2>
        {page.desc && (
          <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 2 }}>{page.desc}</p>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px", position: "relative" }}>
        {/* Search */}
        <div style={{ position: "relative" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "7px 14px", background: "var(--bg-input)",
            border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)",
            width: 260, transition: "all 0.25s ease",
          }}>
            <Search size={14} color="var(--text-muted)" />
            <input
              id="topbar-search"
              placeholder="Search pages, audit logs..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowSearchDropdown(e.target.value.length > 0);
              }}
              onFocus={() => setShowSearchDropdown(searchQuery.length > 0)}
              onBlur={() => setTimeout(() => setShowSearchDropdown(false), 200)}
              onKeyDown={handleSearch}
              style={{
                background: "transparent", border: "none", outline: "none",
                color: "var(--text-secondary)", fontSize: "0.8rem", width: "100%",
                fontFamily: "var(--font-sans)",
              }}
            />
            <kbd style={{
              fontSize: "0.6rem", color: "var(--text-muted)", background: "var(--bg-card)",
              padding: "2px 6px", borderRadius: 4, border: "1px solid var(--border-subtle)",
              fontFamily: "var(--font-mono)", lineHeight: 1,
            }}>⌘K</kbd>
          </div>
          
          {/* Search Dropdown */}
          {showSearchDropdown && (
            <div className="glass-card" style={{ position: "absolute", top: "100%", left: 0, marginTop: 8, width: "100%", padding: 8, zIndex: 50, border: "1px solid var(--border-medium)", display: "flex", flexDirection: "column", gap: 4 }}>
              {searchResults.length > 0 ? (
                searchResults.map((res) => (
                  <button
                    key={res.path}
                    onClick={() => {
                      router.push(res.path);
                      setSearchQuery("");
                      setShowSearchDropdown(false);
                    }}
                    style={{ width: "100%", textAlign: "left", padding: "8px 12px", border: "none", background: "transparent", borderRadius: "var(--radius-xs)", cursor: "pointer", transition: "background 0.2s" }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "var(--bg-hover)"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <p style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "0.8rem" }}>{res.title}</p>
                    <p style={{ color: "var(--text-muted)", fontSize: "0.7rem", marginTop: 2 }}>{res.desc}</p>
                  </button>
                ))
              ) : null}
              
              <button
                onClick={() => {
                  router.push(`/audit?actor=${encodeURIComponent(searchQuery)}`);
                  setSearchQuery("");
                  setShowSearchDropdown(false);
                }}
                style={{ width: "100%", textAlign: "left", padding: "8px 12px", border: "none", background: "transparent", borderRadius: "var(--radius-xs)", cursor: "pointer", transition: "background 0.2s", borderTop: searchResults.length > 0 ? "1px solid var(--border-subtle)" : "none", marginTop: searchResults.length > 0 ? 4 : 0 }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--bg-hover)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                <p style={{ color: "var(--accent-blue)", fontWeight: 600, fontSize: "0.8rem", display: "flex", alignItems: "center", gap: 6 }}>
                  <Search size={12} /> Search audit logs for &quot;{searchQuery}&quot;
                </p>
              </button>
            </div>
          )}
        </div>

        {/* Help */}
        <a
          href="https://github.com/Eternal-prithivi/aws-provision-using-terraform/blob/main/docs/README.md"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            background: "var(--bg-input)", border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)", padding: "8px",
            color: "var(--text-secondary)", cursor: "pointer",
            display: "flex", alignItems: "center",
            transition: "all 0.25s ease", textDecoration: "none"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = "var(--text-primary)";
            e.currentTarget.style.borderColor = "var(--border-medium)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = "var(--text-secondary)";
            e.currentTarget.style.borderColor = "var(--border-subtle)";
          }}
          title="Help Center"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
        </a>

        {/* Notifications */}
        <div style={{ position: "relative" }}>
          <button
            id="topbar-notifications"
            onClick={() => {
              setShowNotifications(!showNotifications);
              if (!showNotifications) loadNotifications();
            }}
            style={{
              background: "var(--bg-input)", border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)", padding: "8px",
              color: showNotifications ? "var(--text-primary)" : "var(--text-secondary)", cursor: "pointer",
              display: "flex", alignItems: "center",
              transition: "all 0.25s ease", position: "relative",
            }}
            title="Notifications"
          >
            <Bell size={16} />
            {notifCount > 0 && (
              <div style={{
                position: "absolute", top: 3, right: 3,
                minWidth: 16, height: 16, borderRadius: "50%",
                background: "linear-gradient(135deg, #f43f5e, #e11d48)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "0.55rem", fontWeight: 700, color: "white",
                boxShadow: "0 0 8px rgba(244,63,94,0.4)",
                padding: "0 4px",
              }}>
                {notifCount > 9 ? "9+" : notifCount}
              </div>
            )}
          </button>
        
          {showNotifications && (
            <div className="glass-card" style={{
              position: "absolute", top: "100%", right: 0, marginTop: 8,
              width: 360, maxHeight: 440, overflow: "hidden", zIndex: 50,
              border: "1px solid var(--border-medium)",
              display: "flex", flexDirection: "column",
            }}>
              <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ fontWeight: 700, fontSize: "0.9rem" }}>Notifications</h4>
                <span className="badge badge-info" style={{ fontSize: "0.65rem" }}>{notifCount} new</span>
              </div>
              <div style={{ overflowY: "auto", flex: 1, maxHeight: 360 }}>
                {notifications.length === 0 ? (
                  <div style={{ padding: 32, textAlign: "center" }}>
                    <Bell size={32} color="var(--text-muted)" style={{ margin: "0 auto 12px", opacity: 0.3 }} />
                    <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>All clear — no notifications</p>
                  </div>
                ) : (
                  notifications.map((n) => {
                    const Icon = NOTIFICATION_ICONS[n.type] || Bell;
                    const color = SEVERITY_COLORS[n.severity] || "var(--text-muted)";
                    return (
                      <button
                        key={n.id}
                        onClick={() => handleNotificationClick(n)}
                        style={{
                          width: "100%", textAlign: "left", padding: "12px 16px",
                          border: "none", background: "transparent",
                          cursor: "pointer", transition: "background 0.2s",
                          borderBottom: "1px solid var(--border-subtle)",
                          display: "flex", gap: 12, alignItems: "flex-start",
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = "rgba(99,102,241,0.04)"}
                        onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                      >
                        <div style={{
                          width: 32, height: 32, borderRadius: "var(--radius-sm)",
                          background: `${color}15`, display: "flex", alignItems: "center",
                          justifyContent: "center", flexShrink: 0, marginTop: 2,
                        }}>
                          <Icon size={15} color={color} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <p style={{ fontWeight: 600, fontSize: "0.8rem", color: "var(--text-primary)" }}>{n.title}</p>
                            <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", whiteSpace: "nowrap", marginLeft: 8 }}>
                              {formatTime(n.timestamp)}
                            </span>
                          </div>
                          <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {n.message}
                          </p>
                        </div>
                        <ExternalLink size={12} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: 4 }} />
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Avatar Menu */}
        <div style={{ position: "relative" }}>
          <div
            id="topbar-user-menu"
            onClick={() => setShowUserMenu(!showUserMenu)}
            style={{
              display: "flex", alignItems: "center", gap: "10px",
              padding: "6px 12px 6px 6px",
              background: "var(--bg-input)", border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-xl)", cursor: "pointer",
              transition: "all 0.25s ease",
            }}
          >
            <div
              style={{
                width: 30, height: 30, borderRadius: "50%",
                background: "linear-gradient(135deg, #6366f1, #a855f7)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "0.7rem", fontWeight: 700, color: "white",
                boxShadow: "0 2px 8px rgba(99,102,241,0.3)",
              }}
            >
              {user?.name?.substring(0, 2).toUpperCase() || "US"}
            </div>
            <div>
              <p style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.2, textTransform: "capitalize" }}>
                {user?.role || "Viewer"}
              </p>
              <p style={{ fontSize: "0.62rem", color: "var(--text-muted)" }}>{user?.username || "user"}</p>
            </div>
          </div>
          
          {showUserMenu && (
            <div className="glass-card" style={{ position: "absolute", top: "100%", right: 0, marginTop: 8, width: 200, padding: 8, zIndex: 50, border: "1px solid var(--border-medium)", display: "flex", flexDirection: "column", gap: 2 }}>
              {/* User Info */}
              <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border-subtle)", marginBottom: 4 }}>
                <p style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--text-primary)" }}>{user?.name || "User"}</p>
                <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 2 }}>@{user?.username || "user"}</p>
                <span className={`badge ${user?.role === "admin" ? "badge-purple" : user?.role === "devops" ? "badge-info" : "badge-success"}`} style={{ marginTop: 6, fontSize: "0.65rem" }}>
                  {user?.role || "viewer"}
                </span>
              </div>
              <button
                onClick={() => { setShowUserMenu(false); router.push("/settings"); }}
                style={{
                  width: "100%", textAlign: "left", padding: "9px 12px",
                  border: "none", background: "transparent", borderRadius: "var(--radius-xs)",
                  cursor: "pointer", display: "flex", alignItems: "center", gap: 10,
                  fontSize: "0.82rem", color: "var(--text-secondary)", transition: "all 0.2s",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-card-hover)"; e.currentTarget.style.color = "var(--text-primary)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--text-secondary)"; }}
              >
                <Settings size={15} /> Settings
              </button>
              <button
                onClick={handleLogout}
                style={{
                  width: "100%", textAlign: "left", padding: "9px 12px",
                  border: "none", background: "transparent", borderRadius: "var(--radius-xs)",
                  cursor: "pointer", display: "flex", alignItems: "center", gap: 10,
                  fontSize: "0.82rem", color: "var(--accent-red)", transition: "all 0.2s",
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--accent-red-glow)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                <LogOut size={15} /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
