import type { ReactNode } from "react";

import { cx, TEXT_TONE, type Tone } from "@/lib/cx";

/** Small uppercase label that heads every card/section in the design. */
export default function SectionLabel({
  children,
  tone = "muted",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <div className={cx("text-xs uppercase tracking-[0.08em]", TEXT_TONE[tone], className)}>{children}</div>
  );
}
