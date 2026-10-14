// OWNER: Person C. "Extracted product profile": name, key numbers and feature-strength bars.
// Feature sliders are display-only in this mockup; make them draggable when wiring edits.
import { Card, ProgressBar, SectionLabel } from "@/components/ui";
import { FEATURE_LABELS } from "@/lib/mock/intake";
import type { ProductProfile } from "@/lib/types";

export default function ProfileCard({ profile, trial = "14 days" }: { profile: ProductProfile; trial?: string }) {
  const pricePeriod = profile.pack === "cafe" ? "visit" : "mo";

  return (
    <Card className="flex flex-col gap-4 !rounded-2xl !p-[22px]">
      <div className="flex items-baseline justify-between">
        <SectionLabel>Extracted product profile</SectionLabel>
        <span className="font-mono text-xs text-teal">auto-filled</span>
      </div>
      <div className="font-display text-[28px] font-bold">{profile.name}</div>
      <div className="flex gap-2.5">
        <KeyValue label="Price" value={`${profile.currency} ${profile.price} / ${pricePeriod}`} />
        <KeyValue label="Trial" value={trial} />
      </div>
      <div>
        <div className="mb-2.5 text-[13px] text-muted">Feature strengths (drag to adjust)</div>
        <div className="flex flex-col gap-3">
          {Object.entries(profile.features).map(([key, v]) => (
            <div key={key} className="flex items-center gap-3 text-sm">
              <span className="w-[100px]">{FEATURE_LABELS[key] ?? key}</span>
              <ProgressBar value={v} className="flex-1" />
              <span className="w-7 text-right font-mono">{v.toFixed(1)}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex-1 rounded-xl bg-bg px-3.5 py-3">
      <div className="text-xs text-muted">{label}</div>
      <div className="font-mono text-xl">{value}</div>
    </div>
  );
}
