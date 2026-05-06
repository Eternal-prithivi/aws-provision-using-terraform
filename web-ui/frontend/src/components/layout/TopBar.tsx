"use client";

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Bell, Search, Settings, LogOut, User as UserIcon } from "lucide-react";

const PAGE_TITLES: Record<string, { title: string; desc: string }> = {
  "/": { title: "Dashboard", desc: "Infrastructure overview at a glance" },
  "/deploy": { title: "Deploy Wizard", desc: "Configure and launch infrastructure" },
  "/policies": { title: "Policy Dashboard", desc: "Security and governance rules" },
  "/audit": { title: "Audit Log", desc: "Deployment history and events" },
  "/team": { title: "Team Management", desc: "Users, roles, and permissions" },
  "/drift": { title: "Drift Detection", desc: "Infrastructure state monitoring" },
};

export default function TopBar() {
  const pathname = usePathname();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [user, setUser] = useState<{ name?: string; username?: string; role?: string } | null>(null);

  useEffect(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem("auth_user") || "{}");
      if (stored.username) setUser(stored);
    } catch {}
  }, [pathname]);

  if (pathname === "/login") return null;

  const page = PAGE_TITLES[pathname] ?? { title: "Dashboard", desc: "" };

  const searchResults = Object.entries(PAGE_TITLES)
    .filter(([path, data]) => 
      data.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
      data.desc.toLowerCase().includes(searchQuery.toLowerCase()) ||
      path.toLowerCase().includes(searchQuery.toLowerCase())
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
              placeholder="Search pages or audit logs..."
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
                  <Search size={12} /> Search audit logs for "{searchQuery}"
                </p>
              </button>
            </div>
          )}
        </div>

        {/* Notifications */}
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
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
            <div style={{
              position: "absolute", top: 4, right: 4, width: 6, height: 6,
              borderRadius: "50%", background: "var(--accent-indigo)",
              boxShadow: "0 0 8px rgba(99,102,241,0.5)",
            }} />
          </button>
          
          {showNotifications && (
            <div className="glass-card" style={{ position: "absolute", top: "100%", right: 0, marginTop: 8, width: 280, padding: 16, zIndex: 50, border: "1px solid var(--border-medium)" }}>
              <h4 style={{ fontWeight: 700, fontSize: "0.85rem", marginBottom: 12 }}>Notifications</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ fontSize: "0.75rem", padding: "8px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                  <p style={{ color: "var(--text-primary)", fontWeight: 600 }}>Policy Check Passed</p>
                  <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Last deployment passed all checks.</p>
                </div>
                <div style={{ fontSize: "0.75rem", padding: "8px 0" }}>
                  <p style={{ color: "var(--text-primary)", fontWeight: 600 }}>System Updated</p>
                  <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Phase 15 features have been rolled out.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* User Avatar Menu */}
        <div style={{ position: "relative" }}>
          <div
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
            <div className="glass-card" style={{ position: "absolute", top: "100%", right: 0, marginTop: 8, width: 160, padding: 8, zIndex: 50, border: "1px solid var(--border-medium)", display: "flex", flexDirection: "column", gap: 4 }}>
              <button className="btn-secondary" onClick={() => { setShowUserMenu(false); router.push("/settings"); }} style={{ width: "100%", justifyContent: "flex-start", padding: "8px 12px", border: "none", background: "transparent" }}>
                <Settings size={14} /> Settings
              </button>
              <button className="btn-danger" onClick={handleLogout} style={{ width: "100%", justifyContent: "flex-start", padding: "8px 12px", border: "none", background: "transparent", color: "var(--accent-red)" }}>
                <LogOut size={14} /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
