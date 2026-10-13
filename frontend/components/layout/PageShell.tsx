import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

// Each screen has a faint coloured glow in a different corner (see the design boards).
const GLOWS = {
  arena: "bg-[radial-gradient(1200px_600px_at_45%_30%,#141b2b_0%,#0b0e14_70%)]",
  intake: "bg-[radial-gradient(900px_500px_at_20%_0%,#172033_0%,#0b0e14_65%)]",
  council: "bg-[radial-gradient(1000px_500px_at_80%_0%,#1a2036_0%,#0b0e14_65%)]",
  compare: "bg-[radial-gradient(1000px_500px_at_10%_0%,#17202f_0%,#0b0e14_65%)]",
  kit: "bg-[radial-gradient(1000px_500px_at_90%_0%,#14262b_0%,#0b0e14_65%)]",
} as const;

/**
 * Full-height page wrapper with the screen's background glow.
 * `padded={false}` is for the Arena screen, which has full-bleed side panels.
 */
export default function PageShell({
  glow,
  children,
  padded = true,
  className,
}: {
  glow: keyof typeof GLOWS;
  children: ReactNode;
  padded?: boolean;
  className?: string;
}) {
  return (
    <div className={cx("flex min-h-screen flex-col", GLOWS[glow], padded && "gap-6 px-10 pb-12 pt-7", className)}>
      {children}
    </div>
  );
}
