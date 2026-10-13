import type { HTMLAttributes } from "react";

import { cx } from "@/lib/cx";

const VARIANTS = {
  /** Standard panel. */
  default: "border border-line bg-surface rounded-[20px] p-6",
  /** Slightly lighter panel, used for the "run these first" band and the Telegram console. */
  raised: "border border-line-2 bg-surface-2 rounded-[20px] p-6",
  /** Highlighted (selected scenario / selected pack). */
  accent: "border-2 border-accent bg-accent-bg rounded-[20px] p-[22px]",
  /** Assumption or trade-off callout. */
  warn: "border border-warn-line bg-warn-bg rounded-[14px] px-[18px] py-4",
  /** Big verdict card. */
  hero: "border border-line-2 rounded-3xl p-9 bg-gradient-to-br from-[#141b2b] to-surface-2",
  /** Small nested tile inside a card. */
  tile: "bg-bg rounded-xl px-3.5 py-3",
  /** Quote or list item inside a card. */
  inset: "bg-surface-3 rounded-[14px] px-4 py-3.5",
} as const;

export type CardVariant = keyof typeof VARIANTS;

export default function Card({
  variant = "default",
  className,
  ...rest
}: { variant?: CardVariant } & HTMLAttributes<HTMLDivElement>) {
  return <div className={cx(VARIANTS[variant], className)} {...rest} />;
}
