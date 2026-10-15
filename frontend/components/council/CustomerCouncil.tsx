// OWNER: Person B. "Customer council · who buys": one quote per segment.
import { Card, SectionLabel } from "@/components/ui";
import { segmentStyle } from "@/lib/theme";

export interface SegmentVoice {
  segment: string;
  pct: number;
  quote: string;
}

export default function CustomerCouncil({ voices }: { voices: SegmentVoice[] }) {
  return (
    <Card className="flex min-w-0 flex-[1_1_380px] flex-col gap-3.5 !rounded-[20px]">
      <SectionLabel tone="teal">Customer council · who buys</SectionLabel>
      {voices.map((v) => {
        const s = segmentStyle(v.segment);
        return (
          <Card key={v.segment} variant="inset">
            <div className="text-xs font-bold" style={{ color: s.color }}>
              {s.label} · {v.pct}% choose you
            </div>
            <div className="mt-1 text-[15px] leading-normal">{v.quote}</div>
          </Card>
        );
      })}
    </Card>
  );
}
