// OWNER: Person A. One official statistic (SingStat). The row is shown exactly as the API returned it.
import { Card, SectionLabel } from "@/components/ui";
import type { Resource } from "@/lib/types";

import { retrieved } from "./ResourceCard";

export default function OfficialDataCard({ r }: { r: Resource }) {
  const [name, ...rest] = r.claim.split(": ");
  return (
    <Card variant="raised" className="flex min-w-0 flex-[1_1_300px] flex-col gap-2 !p-5">
      <SectionLabel tone="teal">{name}</SectionLabel>
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-2xl">{r.value?.toLocaleString("en-GB") ?? "n/a"}</span>
        {r.unit && <span className="text-xs text-muted">{r.unit}</span>}
      </div>
      <p className="m-0 text-sm leading-normal text-ink-soft">{rest.join(": ")}</p>
      <div className="font-mono text-xs text-muted">“{r.quote}”</div>
      <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 pt-1 text-xs text-muted">
        <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-blue underline-offset-2 hover:underline">
          {r.domain}
        </a>
        <span>retrieved {retrieved(r.retrieved_at)}</span>
      </div>
    </Card>
  );
}
