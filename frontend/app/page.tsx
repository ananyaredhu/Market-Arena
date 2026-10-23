import Link from "next/link";

import AppHeader, { DEMO_PROJECT_ID } from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { Card, SectionLabel } from "@/components/ui";

// Screen index for the team. Numbers match the boards in "Market Arena UI Ideas".
const SCREENS = [
  { n: 1, title: "Live Arena + Glass-Box", href: `/project/${DEMO_PROJECT_ID}`, owner: "C (Arena) + A (Glass-Box)" },
  { n: 2, title: "Idea Intake + Packs", href: "/intake", owner: "C" },
  { n: 3, title: "Arena Council verdict", href: `/project/${DEMO_PROJECT_ID}/council`, owner: "B" },
  { n: 4, title: "Scenario compare", href: "/compare", owner: "A" },
  { n: 5, title: "Experiment Kit + Telegram", href: `/project/${DEMO_PROJECT_ID}/kit`, owner: "B (Kit) + C (Telegram)" },
  { n: 6, title: "Resources (reference library)", href: "/resources", owner: "A" },
];

const STANDALONE = [
  { title: "Arena alone", href: "/dev/arena" },
  { title: "Glass-Box alone", href: "/dev/glassbox" },
  { title: "Council panel alone", href: "/dev/council" },
];

export default function Home() {
  return (
    <PageShell glow="intake">
      <AppHeader disclaimer={false} subtitle="Screen index (mockups on mock data)" />
      <p className="max-w-2xl text-sm text-muted">
        Run the API with <code className="font-mono text-ink">make api</code> (mock mode) and these screens load fixtures.
        Layout and look follow the design boards; text is placeholder.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SCREENS.map((s) => (
          <Link key={s.href} href={s.href}>
            <Card variant="raised" className="h-full">
              <SectionLabel tone="accent">Screen {s.n}</SectionLabel>
              <div className="mt-2 font-display text-xl font-bold">{s.title}</div>
              <div className="mt-1 text-sm text-muted">Owner: {s.owner}</div>
            </Card>
          </Link>
        ))}
      </div>
      <SectionLabel>Build one component alone</SectionLabel>
      <div className="flex flex-wrap gap-3 text-sm">
        {STANDALONE.map((s) => (
          <Link key={s.href} href={s.href} className="rounded-full border border-line-3 px-4 py-2 text-ink-soft">
            {s.title}
          </Link>
        ))}
      </div>
    </PageShell>
  );
}
