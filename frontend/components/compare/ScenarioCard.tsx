// OWNER: Person A. One scenario header card. `highlight` outlines the scenario being tested (B).
import { Card, SectionLabel } from "@/components/ui";

export default function ScenarioCard({
  tag,
  price,
  note,
  highlight = false,
}: {
  tag: string;
  price: string;
  note: string;
  highlight?: boolean;
}) {
  return (
    <Card variant={highlight ? "accent" : "raised"} className="min-w-0 flex-[1_1_420px] !p-[22px]">
      <SectionLabel tone={highlight ? "accent" : "muted"}>{tag}</SectionLabel>
      <div className="mt-1.5 font-display text-[34px] font-bold">{price}</div>
      <div className={`mt-1 text-sm ${highlight ? "text-[#c5d0b0]" : "text-soft"}`}>{note}</div>
    </Card>
  );
}
