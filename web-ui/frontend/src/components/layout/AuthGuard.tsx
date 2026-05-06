"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

/**
 * AuthGuard — redirects unauthenticated users to /login.
 *
 * On the login page itself, it renders children without the
 * sidebar/topbar wrapper (login page has its own full-screen layout).
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    // Login page doesn't need auth check
    if (pathname === "/login") {
      setChecked(true);
      setAuthenticated(false);
      return;
    }

    // Check sessionStorage for auth
    const stored = sessionStorage.getItem("auth_user");
    if (stored) {
      try {
        const user = JSON.parse(stored);
        if (user.authenticated) {
          setAuthenticated(true);
          setChecked(true);
          return;
        }
      } catch {
        /* invalid JSON */
      }
    }

    // Not authenticated — redirect to login
    router.replace("/login");
    setChecked(true);
  }, [pathname, router]);

  // Still checking auth
  if (!checked) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
        background: "var(--bg-primary)",
      }}>
        <div className="skeleton" style={{ width: 200, height: 24 }} />
      </div>
    );
  }

  // Login page — render without sidebar/topbar
  if (pathname === "/login") {
    return <div style={{ width: "100%" }}>{children}</div>;
  }

  // Authenticated — render full layout
  if (authenticated) {
    return <>{children}</>;
  }

  // Fallback (redirecting)
  return null;
}
