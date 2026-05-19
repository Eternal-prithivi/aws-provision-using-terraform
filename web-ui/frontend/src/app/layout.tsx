import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import AuthGuard from "@/components/layout/AuthGuard";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AWS Provisioner — Smart Infrastructure Dashboard",
  description:
    "Web UI for the Smart AWS Infrastructure Provisioning System. Manage deployments, policies, team access, and drift detection.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
    >
      <body style={{ display: "flex", minHeight: "100vh" }}>
        <AuthGuard>
          <Sidebar />
          <div
            style={{
              marginLeft: "var(--sidebar-width)",
              flex: 1,
              display: "flex",
              flexDirection: "column",
              minHeight: "100vh",
            }}
          >
            <TopBar />
            <main style={{ flex: 1, padding: "28px 36px" }}>{children}</main>
          </div>
        </AuthGuard>
      </body>
    </html>
  );
}
