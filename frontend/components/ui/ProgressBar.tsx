import { BG_TONE, cx, type Tone } from "@/lib/cx";

/** Horizontal track with a filled portion. `value` is 0..1. */
export default function ProgressBar({
  value,
  tone = "accent",
  height = 8,
  className,
}: {
  value: number;
  tone?: Tone;
  height?: number;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className={cx("rounded-full bg-raised", className)} style={{ height }}>
      <div className={cx("rounded-full transition-[width] duration-1000", BG_TONE[tone])} style={{ width: `${pct}%`, height }} />
    </div>
  );
}
