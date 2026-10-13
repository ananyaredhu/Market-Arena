// OWNER: Person C. Numbered step indicator (intake wizard) and the same style reused for the Kit workflow.
import { Pill } from "@/components/ui";

export default function StepPills({ steps, current, done = [] }: { steps: string[]; current: number; done?: number[] }) {
  return (
    <ol className="m-0 flex list-none flex-wrap gap-2 p-0">
      {steps.map((label, i) => (
        <li key={label} aria-current={i === current ? "step" : undefined}>
          <Pill variant={done.includes(i) ? "done" : i === current ? "active" : "idle"}>
            {done.includes(i) ? "✓ " : `${i + 1} `}
            {label}
          </Pill>
        </li>
      ))}
    </ol>
  );
}
