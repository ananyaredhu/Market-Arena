// OWNER: Person B. "Hypotheses to test": each statement with its pass/fail chip.
import { Card, Pill, SectionLabel } from "@/components/ui";

export default function HypothesisList({ items }: { items: { text: string; pass?: string }[] }) {
  return (
    <Card className="flex min-w-0 flex-[1_1_340px] flex-col gap-3.5">
      <SectionLabel>Hypotheses to test</SectionLabel>
      {items.map((h) => (
        <Card key={h.text} variant="inset" className="!p-4">
          <div className="text-base font-bold leading-[1.35]">{h.text}</div>
          {h.pass && (
            <div className="mt-2.5 flex flex-wrap gap-2">
              <Pill variant="done" className="px-2.5 py-1 text-xs">{h.pass}</Pill>
            </div>
          )}
        </Card>
      ))}
    </Card>
  );
}
