import { segmentStyle } from "@/lib/theme";

/** Round marker coloured by customer segment (legend, quotes, stacked bar keys). */
export default function SegmentDot({ segment, size = 12 }: { segment: string; size?: number }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block shrink-0 rounded-full"
      style={{ width: size, height: size, background: segmentStyle(segment).color }}
    />
  );
}
