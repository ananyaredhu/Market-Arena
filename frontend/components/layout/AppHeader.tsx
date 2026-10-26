import Link from "next/link";
import type { ReactNode } from "react";

import { Pill } from "@/components/ui";
import { DEMO_PROJECT_ID, projectHref, type RunContext } from "@/lib/run-context";

import Logo from "./Logo";

export type NavKey = "arena" | "council" | "history" | "compare" | "experiments";

export { DEMO_PROJECT_ID } from "@/lib/run-context";

const NAV: { key: NavKey; label: string }[] = [
  { key: "arena", label: "Arena" },
  { key: "council", label: "Council" },
  { key: "history", label: "History" },
  { key: "compare", label: "Compare" },
  { key: "experiments", label: "Experiments" },
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
  runContext,
  subtitle,
  meta,
  disclaimer = DISCLAIMER,
  right,
}: {
  active?: NavKey;
  projectId?: string;
  runContext?: RunContext | null;
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
            <Link key={n.key} href={projectHref(projectId, n.key, runContext)} aria-current={n.key === active ? "page" : undefined}>
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
