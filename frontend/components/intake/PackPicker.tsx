"use client";
// OWNER: Person C. Industry pack cards. Controlled: pass `value` and `onChange`.
import { SectionLabel } from "@/components/ui";
import { cx } from "@/lib/cx";
import type { PackOption } from "@/lib/mock/intake";

export default function PackPicker({
  packs,
  value,
  onChange,
}: {
  packs: PackOption[];
  value: string;
  onChange?: (id: string) => void;
}) {
  return (
    <section>
      <SectionLabel className="mb-3">Industry pack · detected from your text</SectionLabel>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {packs.map((p) => {
          const selected = p.id === value;
          return (
            <button
              key={p.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange?.(p.id)}
              className={cx(
                "rounded-2xl p-[18px] text-left",
                selected && "border-2 border-accent bg-accent-bg",
                !selected && p.state === "custom" && "border border-dashed border-line-dashed",
                !selected && p.state !== "custom" && "border border-line-2 bg-surface-2",
              )}
            >
              {selected ? (
                <span className="inline-block rounded-full bg-accent px-2.5 py-[3px] text-xs font-bold text-bg">Selected</span>
              ) : (
                <span className={cx("block py-[3px] text-xs", p.state === "custom" ? "text-amber" : "text-muted")}>{p.tag}</span>
              )}
              <div className="mt-2.5 font-display text-[22px] font-bold">{p.name}</div>
              <div className="mt-1.5 text-[13px] leading-normal text-soft">{p.blurb}</div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
