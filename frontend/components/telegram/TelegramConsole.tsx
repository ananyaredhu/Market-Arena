"use client";
// OWNER: Person C. MOCKUP of the Telegram A/B console: variants, consent notice with approve gate, results preview.
// Real flow (Master Plan section 10): nothing is sent until the founder approves; only opted-in contacts get messages.
import { Button, Card, SectionLabel } from "@/components/ui";
import { cx } from "@/lib/cx";

export interface TelegramResult {
  variant: string;
  rate: number; // percent
}

export default function TelegramConsole({
  contacts,
  variants,
  variantSizes,
  results,
  onApprove,
  onEdit,
  live = false,
}: {
  live?: boolean;
  contacts: number;
  variants: string[];
  variantSizes: number[];
  results: TelegramResult[];
  onApprove?: () => void;
  onEdit?: () => void;
}) {
  const best = Math.max(...results.map((r) => r.rate));
  return (
    <Card variant="raised" className="flex min-w-0 flex-[1_1_360px] flex-col gap-3.5">
      <div className="flex items-center justify-between">
        <SectionLabel tone="blue">{live ? "Telegram A/B console · observed" : "Telegram A/B console · simulated"}</SectionLabel>
        <span className="font-mono text-xs text-muted">{contacts} opted-in contacts</span>
      </div>

      <div className="flex gap-3">
        {variants.slice(0, 2).map((text, i) => (
          <div key={text} className="min-w-0 flex-1">
            <div className="mb-1.5 text-xs text-muted">
              Variant {"AB"[i]} · {variantSizes[i]} contacts
            </div>
            <div className="rounded-[16px_16px_16px_4px] bg-tg p-3.5 text-sm leading-[1.45]">
              {text}
              <div className="mt-2.5 rounded-lg bg-tg-button p-2 text-center text-[13px] font-bold">{live ? "Interested · Too expensive · Learn more" : "Try 14 days free"}</div>
            </div>
          </div>
        ))}
      </div>

      <Card variant="warn" className="!px-4 !py-3.5">
        <div className="text-sm leading-normal text-warn-ink">
          Nothing is sent until you approve. Only people who pressed Start on your bot receive messages, and they can send
          /stop at any time.
        </div>
        {!live && <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="primary" disabled={!onApprove} onClick={onApprove}>Approve &amp; send</Button>
          <Button variant="warn" disabled={!onEdit} onClick={onEdit}>Edit variants</Button>
        </div>}
      </Card>

      <SectionLabel className="mt-1">{live ? "Interested / delivered · real results" : "Preview of results panel · sample"}</SectionLabel>
      <div className="flex flex-col gap-2.5">
        {results.map((r) => (
          <div key={r.variant} className="flex items-center gap-2.5 text-[13px]">
            <span className="w-5">{r.variant}</span>
            <div className="h-3 flex-1 rounded-md bg-raised">
              <div
                className={cx("h-3 rounded-md", r.rate === best ? "bg-accent" : "bg-slate")}
                style={{ width: `${best > 0 ? (r.rate / (best * 1.6)) * 100 : 0}%` }}
              />
            </div>
            <span className="font-mono">{r.rate}%</span>
          </div>
        ))}
      </div>
      <div className="text-[13px] leading-normal text-soft">
        Tiny samples are signals, not proof. Review these responses alongside the simulation before deciding what to test next.
      </div>
    </Card>
  );
}
