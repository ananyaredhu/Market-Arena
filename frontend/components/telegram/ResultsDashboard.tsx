import { Card, SectionLabel, Stat } from "@/components/ui";

export type ObservedVariant = {
  variant: string;
  sent: number;
  interested: number;
  too_expensive: number;
  clicks: number;
  replies: number;
  unsubscribes: number;
};

export type ObservedResults = {
  approved: boolean;
  contacts: number;
  variant_sizes: number[];
  variants: ObservedVariant[];
  delivery_statuses: Record<string, number>;
  deferred_reasons: Record<string, number>;
};

const metric = (variants: ObservedVariant[], key: keyof ObservedVariant) =>
  variants.reduce((total, variant) => total + Number(variant[key] ?? 0), 0);

export default function ResultsDashboard({ results }: { results: ObservedResults }) {
  const cards = [
    ["Deliveries", metric(results.variants, "sent")],
    ["Interested", metric(results.variants, "interested")],
    ["Too expensive", metric(results.variants, "too_expensive")],
    ["Learn more", metric(results.variants, "clicks")],
    ["Replies", metric(results.variants, "replies")],
    ["Unsubscribes", metric(results.variants, "unsubscribes")],
    ["Active contacts", results.contacts],
  ] as const;
  return (
    <section aria-labelledby="observed-results-heading" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="observed-results-heading" className="text-lg text-ink">Observed Telegram engagement</h2>
          <p className="text-sm text-muted">Real tester responses, separate from simulated market outcomes.</p>
        </div>
        <span className="rounded-full border border-line-3 px-3 py-1 text-xs text-muted">
          {results.approved ? "Approved" : "Not approved"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 lg:grid-cols-7">
        {cards.map(([label, value]) => <Stat key={label} value={value} caption={label} />)}
      </div>
      <Card variant="inset" className="flex flex-col gap-3 overflow-x-auto">
        <SectionLabel>Observed results by variant</SectionLabel>
        <table className="w-full min-w-[680px] text-left text-xs">
          <caption className="sr-only">Observed Telegram engagement by variant</caption>
          <thead className="text-muted"><tr>
            <th scope="col" className="pb-2 pr-3">Variant</th><th scope="col" className="pb-2 pr-3">Contacts</th>
            <th scope="col" className="pb-2 pr-3">Sent</th><th scope="col" className="pb-2 pr-3">Interested</th>
            <th scope="col" className="pb-2 pr-3">Too expensive</th><th scope="col" className="pb-2 pr-3">Learn more</th>
            <th scope="col" className="pb-2 pr-3">Replies</th><th scope="col">Unsubscribes</th>
          </tr></thead>
          <tbody>{results.variants.map((variant, index) => <tr key={variant.variant} className="border-t border-line">
            <th scope="row" className="py-2 pr-3 font-medium text-ink">{variant.variant}</th>
            <td className="py-2 pr-3">{results.variant_sizes[index] ?? 0}</td><td className="py-2 pr-3">{variant.sent}</td>
            <td className="py-2 pr-3">{variant.interested}</td><td className="py-2 pr-3">{variant.too_expensive}</td>
            <td className="py-2 pr-3">{variant.clicks}</td><td className="py-2 pr-3">{variant.replies}</td>
            <td className="py-2">{variant.unsubscribes}</td>
          </tr>)}</tbody>
        </table>
      </Card>
      <p className="text-xs text-muted">
        Delivery statuses: {JSON.stringify(results.delivery_statuses)} · Deferred reasons: {JSON.stringify(results.deferred_reasons)}
      </p>
    </section>
  );
}
