import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

const VARIANTS = {
  /** Neutral outlined chip (e.g. "Also generated" items, disclaimer). */
  outline: "border border-line-3 text-ink-soft",
  /** Current step / selected nav item. */
  active: "bg-accent text-bg font-bold",
  /** Active nav item on dark chrome. */
  nav: "bg-raised text-ink",
  /** Completed step. */
  done: "border border-teal text-teal",
  /** Upcoming step or inactive item. */
  idle: "border border-line-3 text-muted",
  /** Inactive nav item (no border). */
  navIdle: "text-muted",
} as const;

export default function Pill({
  variant = "outline",
  children,
  className,
}: {
  variant?: keyof typeof VARIANTS;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={cx("inline-block rounded-full px-3.5 py-1.5 text-[13px]", VARIANTS[variant], className)}>
      {children}
    </span>
  );
}
