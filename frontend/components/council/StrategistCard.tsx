// OWNER: Person B. "Competitor strategist · likely reaction".
import { Card, SectionLabel, Stat } from "@/components/ui";

export default function StrategistCard({
  headline,
  explanation,
  shareImpact,
  moves,
}: {
  headline: string;
  explanation: string;
  shareImpact: string;
  moves: string;
}) {
  return (
    <Card className="flex min-w-0 flex-[1_1_380px] flex-col gap-3.5">
      <SectionLabel tone="blue">Competitor strategist · likely reaction</SectionLabel>
      <div className="font-display text-2xl font-bold leading-tight">{headline}</div>
      <div className="text-[15px] leading-normal text-soft">{explanation}</div>
      <div className="flex gap-2.5">
        <Stat value={shareImpact} caption="your share" tone="coral" />
        <Stat value={moves} caption="moves simulated" />
      </div>
    </Card>
  );
}
