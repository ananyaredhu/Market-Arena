// OWNER: Person C. Amber callout listing what the intake could not infer.
import { Card, SectionLabel } from "@/components/ui";

export default function MissingAssumptions({ items }: { items: { question: string; hint?: string }[] }) {
  return (
    <Card variant="warn" className="mt-2">
      <SectionLabel tone="amber" className="mb-2.5">
        {items.length} assumptions still missing
      </SectionLabel>
      <ul className="m-0 list-disc pl-[18px] text-[15px] leading-[1.7] text-warn-ink">
        {items.map((i) => (
          <li key={i.question}>
            {i.question} {i.hint && <span className="text-amber">{i.hint}</span>}
          </li>
        ))}
      </ul>
    </Card>
  );
}
