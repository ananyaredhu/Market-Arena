// OWNER: Person A. Amber callout for what the model cannot price (revenue vs share, etc.).
import { Card, SectionLabel } from "@/components/ui";

export default function TradeoffNote({ children }: { children: React.ReactNode }) {
  return (
    <Card variant="warn" className="min-w-0 flex-[1_1_420px] !rounded-[20px] !p-6">
      <SectionLabel tone="amber" className="mb-2.5">Trade-off the model can’t price for you</SectionLabel>
      <div className="text-base leading-[1.55] text-warn-ink">{children}</div>
    </Card>
  );
}
