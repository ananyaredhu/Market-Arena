"use client";
// OWNER: Person C. Segmented buttons that switch the scenario shown in the Arena (e.g. three price points).
import { SectionLabel } from "@/components/ui";
import { cx } from "@/lib/cx";

export interface ScenarioChoice {
  id: string;
  label: string;
}

export default function ScenarioPicker({
  title,
  choices,
  value,
  onChange,
  summary,
}: {
  title: string;
  choices: ScenarioChoice[];
  value: string;
  onChange: (id: string) => void;
  summary?: string;
}) {
  return (
    <section>
      <SectionLabel className="mb-2.5">{title}</SectionLabel>
      <div className="flex gap-1.5">
        {choices.map((c) => {
          const on = c.id === value;
          return (
            <button
              key={c.id}
              type="button"
              aria-pressed={on}
              onClick={() => onChange(c.id)}
              className={cx(
                "min-h-11 flex-1 rounded-[10px] border text-[15px] font-bold",
                on ? "border-accent bg-accent text-bg" : "border-line-3 bg-transparent text-ink",
              )}
            >
              {c.label}
            </button>
          );
        })}
      </div>
      {summary && <div className="mt-2.5 text-[13px] leading-normal text-muted">{summary}</div>}
    </section>
  );
}
