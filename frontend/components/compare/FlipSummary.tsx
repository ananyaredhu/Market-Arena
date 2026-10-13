// OWNER: Person A. "What would flip the market": aggregate of every agent's flip, as plain sentences.
import { Card, SectionLabel } from "@/components/ui";
import { cx, TEXT_TONE, type Tone } from "@/lib/cx";

export default function FlipSummary({ items }: { items: { pct: string; tone: Tone; text: string }[] }) {
  return (
    <Card className="min-w-0 flex-[1_1_420px]">
      <SectionLabel tone="accent" className="mb-3.5">What would flip the market · aggregated from every agent</SectionLabel>
      <div className="flex flex-col gap-3 text-base leading-normal">
        {items.map((i) => (
          <div key={i.text} className="flex items-baseline gap-3.5">
            <span className={cx("w-[70px] shrink-0 font-mono text-2xl", TEXT_TONE[i.tone])}>{i.pct}</span>
            <span>{i.text}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
