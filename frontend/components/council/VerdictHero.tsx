// OWNER: Person B. Moderator verdict: headline, confidence derived from fragility, two headline numbers.
import { Card, SectionLabel, Stat } from "@/components/ui";
import { cx, TEXT_TONE, type Tone } from "@/lib/cx";

const CONFIDENCE_TONE: Record<string, Tone> = { low: "coral", medium: "amber", high: "teal" };

export default function VerdictHero({
  verdict,
  runId,
  confidence,
  fragility,
  stats,
}: {
  verdict: string;
  runId: string;
  confidence: "low" | "medium" | "high";
  fragility: number; // 0 robust .. 1 fragile
  stats: { value: string; caption: string; tone?: Tone; captionTone?: Tone }[];
}) {
  return (
    <Card variant="hero" className="flex flex-wrap items-center gap-8">
      <div className="min-w-0 flex-[1_1_520px]">
        <SectionLabel tone="accent" className="tracking-widest">Moderator verdict</SectionLabel>
        <h1 className="mb-0 mt-3 font-display text-[40px] font-bold leading-[1.12] tracking-[-0.015em]">{verdict}</h1>
        <p className="mt-3.5 text-base leading-[1.55] text-soft">
          Every claim below links to {runId}. Confidence is derived from fragility, not from how convincing the prose sounds.
        </p>
      </div>
      <div className="flex flex-[0_0_300px] flex-col gap-3.5">
        <div className="flex items-baseline justify-between">
          <span className="text-[13px] text-muted">Confidence</span>
          <span className={cx("font-display text-[28px] font-bold capitalize", TEXT_TONE[CONFIDENCE_TONE[confidence]])}>
            {confidence}
          </span>
        </div>
        <div>
          <div
            className="relative h-2.5 rounded-full"
            style={{ backgroundImage: "linear-gradient(90deg,#34D3BE 0%,#F6B93B 55%,#FF7A6B 100%)" }}
          >
            <div className="absolute -top-[5px] h-5 w-1 rounded-sm bg-white" style={{ left: `${fragility * 100}%` }} />
          </div>
          <div className="mt-1.5 flex justify-between text-xs text-muted">
            <span>robust</span>
            <span className="font-mono">fragility {fragility.toFixed(2)}</span>
            <span>fragile</span>
          </div>
        </div>
        <div className="flex gap-2.5">
          {stats.map((s) => (
            <Stat key={s.caption} value={s.value} caption={s.caption} tone={s.tone} captionTone={s.captionTone} />
          ))}
        </div>
      </div>
    </Card>
  );
}
