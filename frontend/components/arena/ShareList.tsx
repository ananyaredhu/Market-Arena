// OWNER: Person C. "Who chose what": one row per option with share, bar and p10-p90 range.
import { ProgressBar, SectionLabel } from "@/components/ui";
import { optionStyle } from "@/lib/theme";
import type { RunResult } from "@/lib/types";

const pct = (x: number) => Math.round(x * 100);

export default function ShareList({ runResult, title = "Who chose what · p10–p90" }: { runResult: RunResult; title?: string }) {
  return (
    <section>
      <SectionLabel className="mb-3">{title}</SectionLabel>
      <div className="flex flex-col gap-3.5">
        {runResult.option_ids.map((id) => {
          const t = runResult.totals[id];
          const o = optionStyle(id);
          return (
            <div key={id}>
              <div className="flex items-baseline justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="inline-block h-2.5 w-2.5 rounded-full border-2"
                    style={{ borderColor: o.color, borderStyle: o.dashed ? "dashed" : "solid" }}
                  />
                  {o.label}
                </span>
                <span className="font-mono font-medium">{pct(t.share)}%</span>
              </div>
              <ProgressBar value={t.share / 0.6} height={6} className="mt-1.5" />
              <div className="mt-1 font-mono text-xs text-muted">
                {pct(t.p10)}% – {pct(t.p90)}% · {t.count} dots
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
