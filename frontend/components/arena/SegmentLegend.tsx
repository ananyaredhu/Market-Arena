// OWNER: Person C. Colour key for customer segments. Pass the segment ids present in the run.
import { SectionLabel, SegmentDot } from "@/components/ui";
import { segmentStyle } from "@/lib/theme";

export default function SegmentLegend({ segments, title = "Segments" }: { segments: string[]; title?: string }) {
  return (
    <section>
      <SectionLabel className="mb-2.5">{title}</SectionLabel>
      <div className="flex flex-col gap-2 text-sm">
        {segments.map((s) => (
          <div key={s} className="flex items-center gap-2.5">
            <SegmentDot segment={s} />
            {segmentStyle(s).label}
          </div>
        ))}
      </div>
    </section>
  );
}
