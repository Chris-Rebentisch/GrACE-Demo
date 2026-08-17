"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/chat", label: "Chat" },
  { href: "/inspector", label: "Inspector" },
  { href: "/sources", label: "Sources" },
  { href: "/ingestion", label: "Ingestion" },
  { href: "/claims", label: "Claims" },
  { href: "/onboarding", label: "Onboarding" },
  { href: "/communications/profiles", label: "Voice" },
  { href: "/settings", label: "Settings" },
] as const;

export function AppNav() {
  const pathname = usePathname();
  return (
    <nav
      data-testid="app-nav"
      className="flex items-center gap-1 px-4 py-1 border-b border-border bg-white"
      aria-label="Primary"
    >
      {TABS.map((tab) => {
        const active = pathname === tab.href || pathname?.startsWith(`${tab.href}/`);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            data-testid={`nav-tab-${tab.label.toLowerCase()}`}
            aria-current={active ? "page" : undefined}
            className={cn(
              "rounded-md px-3 py-1 text-xs font-medium transition-colors",
              active
                ? "bg-slate-800 text-white"
                : "text-slate-700 hover:bg-slate-100",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
