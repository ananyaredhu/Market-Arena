import Link from "next/link";
import type { ReactNode } from "react";

import { Pill } from "@/components/ui";

import Logo from "./Logo";

export type NavKey = "arena" | "council" | "compare" | "experiments";

export const DEMO_PROJECT_ID = "proj_1";

const NAV: { key: NavKey; label: string; href: (id: string) => string }[] = [
  { key: "arena", label: "Arena", href: (id) => `/project/${id}` },
  { key: "council", label: "Council", href: (id) => `/project/${id}/council` },
  { key: "compare", label: "Compare", href: () => "/compare" },
  { key: "experiments", label: "Experiments", href: (id) => `/project/${id}/kit` },
];

export const DISCLAIMER = "Simulated outcome under stated assumptions";

/**
 * Top bar used on every screen.
 * - `active`: highlights a nav pill (omit on screens without the nav, e.g. intake).
 * - `subtitle`: breadcrumb-style text next to the logo (used instead of nav on some screens).
 * - `meta`: monospace run info on the right (project, pack, run id, seed).
 * - `right`: any extra node (e.g. an export button or the step pills).
 */
export default function AppHeader({
  active,
  projectId = DEMO_PROJECT_ID,
  subtitle,
  meta,
  disclaimer = DISCLAIMER,
  right,
}: {
  active?: NavKey;
  projectId?: string;
  subtitle?: ReactNode;
  meta?: ReactNode;
  disclaimer?: string | false;
  right?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-center gap-x-6 gap-y-3">
      <Logo />
      {active && (
        <nav className="flex gap-1.5 text-sm" aria-label="Main">
          {NAV.map((n) => (
            <Link key={n.key} href={n.href(projectId)} aria-current={n.key === active ? "page" : undefined}>
              <Pill variant={n.key === active ? "nav" : "navIdle"} className="px-3.5 py-[7px] text-sm">
                {n.label}
              </Pill>
            </Link>
          ))}
        </nav>
      )}
      {subtitle && <span className="text-sm text-muted">{subtitle}</span>}
      <div className="flex-1" />
      {meta && <div className="font-mono text-xs text-muted">{meta}</div>}
      {disclaimer && <Pill variant="outline" className="text-xs">{disclaimer}</Pill>}
      {right}
    </header>
  );
}
