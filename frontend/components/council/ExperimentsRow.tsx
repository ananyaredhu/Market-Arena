// OWNER: Person B. "Run these three experiments first": ranked experiment tiles from CouncilOutput.experiments.
import { Card, SectionLabel } from "@/components/ui";
import type { Experiment } from "@/lib/types";

export default function ExperimentsRow({ experiments }: { experiments: Experiment[] }) {
  return (
    <Card variant="raised">
      <SectionLabel tone="accent" className="mb-3.5">
        Run these three experiments first · ranked by information gained per dollar
      </SectionLabel>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {experiments.slice(0, 3).map((e, i) => (
          <div key={e.title} className="rounded-[14px] bg-bg p-[18px]">
            <div className="font-mono text-xs text-muted">
              {String(i + 1).padStart(2, "0")} · {e.kind}
            </div>
            <div className="mt-1.5 text-[17px] font-bold">{e.title}</div>
            <div className="mt-1.5 text-sm leading-normal text-soft">{e.hypothesis}</div>
            <div className="mt-2 font-mono text-xs text-accent">Pass: {e.pass_threshold}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
