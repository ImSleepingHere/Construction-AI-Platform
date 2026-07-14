import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import Link from "next/link";

import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { SidebarNav } from "@/components/sidebar-nav";
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Construction AI Platform",
  description: "AI agent framework for construction project management.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="h-full">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <div className="flex h-full">
            <aside className="hidden w-60 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground md:flex">
              <div className="flex h-14 items-center border-b px-4">
                <Link href="/" className="font-semibold tracking-tight">
                  Construction AI
                </Link>
              </div>
              <ScrollableNav />
              <div className="mt-auto border-t px-4 py-3 text-xs text-muted-foreground">
                Model: gemini-2.5-flash-lite
              </div>
            </aside>

            <div className="flex min-w-0 flex-1 flex-col">
              <header className="flex h-14 shrink-0 items-center justify-between border-b px-4 md:px-6">
                <span className="text-sm font-medium text-muted-foreground md:hidden">
                  Construction AI
                </span>
                <span className="hidden text-sm text-muted-foreground md:inline">
                  Construction project management, backed by AI agents
                </span>
                <ThemeToggle />
              </header>

              <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
            </div>
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}

function ScrollableNav() {
  return (
    <div className="flex-1 overflow-y-auto">
      <SidebarNav />
    </div>
  );
}
