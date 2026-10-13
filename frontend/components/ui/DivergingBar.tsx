import { cx } from "@/lib/cx";

/**
 * Centre-anchored bar: positive values extend right (blue), negative extend left (accent).
 * `value` is -1..1. Used for the Glass-Box utility breakdown.
 */
export default function DivergingBar({
  label,
  value,
  display,
  className,
}: {
  label: string;
  value: number;
  display?: string;
  className?: string;
}) {
  const width = Math.min(1, Math.abs(value)) * 50;
  const positive = value >= 0;
  return (
    <div className={cx("flex items-center gap-2.5", className)}>
      <span className="w-16 text-[13px]">{label}</span>
      <div className="relative h-3.5 flex-1">
        <div className="absolute inset-y-0 left-1/2 w-px bg-line-3" />
        <div
          className={cx("absolute top-0 h-3.5", positive ? "left-1/2 rounded-r bg-blue" : "right-1/2 rounded-l bg-accent")}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="w-9 text-right font-mono text-xs">
        {display ?? `${positive ? "+" : "−"}${Math.abs(value).toFixed(1)}`}
      </span>
    </div>
  );
}
