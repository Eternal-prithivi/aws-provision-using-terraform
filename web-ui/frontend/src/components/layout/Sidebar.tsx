"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Rocket,
  ShieldCheck,
  FileText,
  Users,
  Activity,
  CloudCog,
  LogOut,
  TerminalSquare,
  Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, desc: "Overview" },
  { href: "/deploy", label: "Deploy Wizard", icon: Rocket, desc: "Infrastructure" },
  { href: "/policies", label: "Policies", icon: ShieldCheck, desc: "Security rules" },
  { href: "/audit", label: "Audit Log", icon: FileText, desc: "Event history" },
  { href: "/team", label: "Team", icon: Users, desc: "Members & roles" },
  { href: "/drift", label: "Drift Detection", icon: Activity, desc: "State monitoring" },
  { href: "/terminal", label: "CloudShell", icon: TerminalSquare, desc: "Web terminal" },
  { href: "/settings", label: "Settings", icon: Settings, desc: "Configuration" },
];

export default function Sidebar() {
  const pathname = usePathname();

  // Don't render sidebar on login page
  if (pathname === "/login") return null;

  return (
    <aside
      style={{
        width: "var(--sidebar-width)",
        minHeight: "100vh",
        background: "var(--bg-sidebar)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        position: "fixed",
        top: 0,
        left: 0,
        zIndex: 50,
        overflow: "hidden",
      }}
    >
      {/* Decorative gradient orb */}
      <div
        style={{
          position: "absolute",
          top: -40,
          left: -40,
          width: 200,
          height: 200,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99,102,241,0.08), transparent 70%)",
          pointerEvents: "none",
        }}
      />

      {/* Branding */}
      <div style={{ padding: "28px 24px 24px", borderBottom: "1px solid var(--border-subtle)", position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: 42,
              height: 42,
              borderRadius: "var(--radius-md)",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 20px rgba(99,102,241,0.3)",
            }}
          >
            <CloudCog size={22} color="white" />
          </div>
          <div>
            <h1
              style={{
                fontSize: "1.05rem",
                fontWeight: 800,
                color: "var(--text-primary)",
                lineHeight: 1.2,
                letterSpacing: "-0.01em",
              }}
            >
              AWS Provisioner
            </h1>
            <p
              style={{
                fontSize: "0.72rem",
                color: "var(--text-muted)",
                marginTop: 3,
                letterSpacing: "0.02em",
              }}
            >
              Smart Infrastructure System
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: "16px 14px", overflowY: "auto" }}>
        <p style={{ fontSize: "0.65rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", padding: "0 12px", marginBottom: 10 }}>
          Navigation
        </p>
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {NAV_ITEMS.map(({ href, label, icon: Icon, desc }) => {
            const active = pathname === href;
            return (
              <li key={href} style={{ marginBottom: 3 }}>
                <Link
                  href={href}
                  className="focus-ring"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "14px",
                    padding: "11px 14px",
                    borderRadius: "var(--radius-md)",
                    textDecoration: "none",
                    position: "relative",
                    overflow: "hidden",
                    transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
                    ...(active
                      ? {
                          background: "linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08))",
                          borderLeft: "none",
                        }
                      : {
                          background: "transparent",
                        }),
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                      e.currentTarget.style.transform = "translateX(4px)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "transparent";
                      e.currentTarget.style.transform = "translateX(0)";
                    }
                  }}
                >
                  {/* Active indicator bar */}
                  {active && (
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        top: "20%",
                        bottom: "20%",
                        width: 3,
                        borderRadius: "0 4px 4px 0",
                        background: "linear-gradient(180deg, #6366f1, #a855f7)",
                      }}
                    />
                  )}
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: active ? "rgba(99,102,241,0.15)" : "rgba(255,255,255,0.03)",
                      transition: "all 0.25s ease",
                      flexShrink: 0,
                    }}
                  >
                    <Icon
                      size={18}
                      color={active ? "#818cf8" : "var(--text-muted)"}
                      style={{ transition: "color 0.25s ease" }}
                    />
                  </div>
                  <div>
                    <p
                      style={{
                        fontSize: "0.875rem",
                        fontWeight: active ? 600 : 500,
                        color: active ? "var(--text-primary)" : "var(--text-secondary)",
                        lineHeight: 1.3,
                        transition: "color 0.25s ease",
                      }}
                    >
                      {label}
                    </p>
                    <p
                      style={{
                        fontSize: "0.68rem",
                        color: "var(--text-muted)",
                        marginTop: 1,
                      }}
                    >
                      {desc}
                    </p>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <p style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Phase 15 • v1.3</p>
            <p style={{ fontSize: "0.65rem", color: "var(--text-muted)", opacity: 0.6, marginTop: 2 }}>Custom Policies + Settings</p>
          </div>
          <Link href="/login" style={{ color: "var(--text-muted)", transition: "color 0.2s" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--accent-red)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-muted)"; }}>
            <LogOut size={16} />
          </Link>
        </div>
      </div>
    </aside>
  );
}
