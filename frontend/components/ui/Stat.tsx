import type { ReactNode } from "react";

import { cx, TEXT_TONE, type Tone } from "@/lib/cx";

/** Big monospace number with a small caption underneath, inside a dark tile. */
export default function Stat({
  value,
  caption,
  tone,
  captionTone = "muted",
  className,
}: {
  value: ReactNode;
  caption: ReactNode;
  tone?: Tone;
  captionTone?: Tone;
  className?: string;
}) {
  return (
    <div className={cx("flex-1 rounded-xl bg-bg px-3.5 py-3", className)}>
      <div className={cx("font-mono text-2xl", tone && TEXT_TONE[tone])}>{value}</div>
      <div className={cx("text-xs", TEXT_TONE[captionTone])}>{caption}</div>
    </div>
  );
}
