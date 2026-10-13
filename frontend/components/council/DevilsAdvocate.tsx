// OWNER: Person B. "Devil's advocate · how this fails": share before -> after each shock, as bars.
import { Card, ProgressBar, SectionLabel } from "@/components/ui";
import type { Perturbation } from "@/lib/mock/council";

export default function DevilsAdvocate({ items, baseline }: { items: Perturbation[]; baseline: number }) {
  return (
    <Card className="flex min-w-0 flex-[1_1_380px] flex-col gap-4">
      <SectionLabel tone="coral">Devil’s advocate · how this fails</SectionLabel>
      <div className="flex flex-col gap-3.5">
        {items.map((p) => (
          <div key={p.label}>
            <div className="flex justify-between text-sm">
              <span>{p.label}</span>
              <span className={`font-mono ${p.severity === "high" ? "text-coral" : "text-amber"}`}>
                {p.from}% → {p.to}%
              </span>
            </div>
            <ProgressBar value={p.to / baseline} tone={p.severity === "high" ? "coral" : "amber"} height={10} className="mt-1.5" />
          </div>
        ))}
      </div>
      <div className="text-[13px] leading-normal text-muted">
        Bars show remaining share versus the {baseline}% baseline. Perturbations are applied to priors, then the engine is
        re-run, so no number here comes from the language model.
      </div>
    </Card>
  );
}
