"use client";
// OWNER: Person A. "Resources": everything the evidence researcher read, kept for you to check. Real data from
// GET /resources. Reference only: nothing on this page changes the simulation (only official datasets do, and the
// Evidence log on a population says exactly which).
import { useEffect, useMemo, useState } from "react";

import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import OfficialDataCard from "@/components/resources/OfficialDataCard";
import ResourceCard from "@/components/resources/ResourceCard";
import ResourceFilters from "@/components/resources/ResourceFilters";
import { Card, SectionLabel } from "@/components/ui";
import { api } from "@/lib/api";
import type { Resource, ResourcesResponse } from "@/lib/types";

const errorText = (e: unknown) => (e instanceof Error ? e.message : "The resources could not be loaded.");

export default function ResourcesPage() {
  const [items, setItems] = useState<Resource[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pack, setPack] = useState("");
  const [topic, setTopic] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    api<ResourcesResponse>("/resources")
      .then((d) => setItems(d.items))
      .catch((e) => setError(errorText(e)));
  }, []);

  const packs = useMemo(() => [...new Set((items ?? []).map((r) => r.pack))].sort(), [items]);
  const inPack = useMemo(() => (items ?? []).filter((r) => !pack || r.pack === pack), [items, pack]);
  const topics = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of inPack) if (r.kind === "page") counts[r.topic] = (counts[r.topic] ?? 0) + 1;
    return counts;
  }, [inPack]);

  const needle = query.trim().toLowerCase();
  const matches = (r: Resource) => !needle || `${r.claim} ${r.quote} ${r.domain}`.toLowerCase().includes(needle);
  const official = inPack.filter((r) => r.kind === "dataset" && matches(r));
  const pages = inPack.filter((r) => r.kind === "page" && (!topic || r.topic === topic) && matches(r));

  return (
    <PageShell glow="compare" className="!gap-[26px]">
      <AppHeader active="resources" subtitle="Reference library" />

      <Card variant="warn">
        <p className="m-0 text-sm leading-normal text-warn-ink">
          <strong>Reference only.</strong> These are surveys, news, prices and official statistics the researcher found,
          each with the exact quote and a link so you can check it. They do not feed the simulation. Only official
          datasets change a prior, and the population&apos;s evidence log says which.
        </p>
      </Card>

      {error && (
        <p role="alert" className="m-0 text-sm text-coral">
          {error}
        </p>
      )}
      {!items && !error && <p className="text-muted">Loading resources…</p>}

      {items && items.length === 0 && (
        <Card>
          <SectionLabel className="mb-2">Nothing here yet</SectionLabel>
          <p className="m-0 text-sm leading-normal text-ink-soft">
            The library fills whenever the evidence researcher runs (<code className="font-mono">POST /evidence/research</code>,
            or a population created with <code className="font-mono">research: true</code>). Singapore runs also add official
            statistics from SingStat.
          </p>
        </Card>
      )}

      {items && items.length > 0 && (
        <>
          <ResourceFilters
            packs={packs}
            pack={pack}
            onPack={(p) => {
              setPack(p);
              setTopic("");
            }}
            topics={topics}
            topic={topic}
            onTopic={setTopic}
            query={query}
            onQuery={setQuery}
          />

          {official.length > 0 && !topic && (
            <section className="flex flex-col gap-3">
              <SectionLabel tone="teal">Official statistics · {official.length}</SectionLabel>
              <div className="flex flex-wrap gap-4">
                {official.map((r) => (
                  <OfficialDataCard key={r.id} r={r} />
                ))}
              </div>
            </section>
          )}

          <section className="flex flex-col gap-3">
            <SectionLabel tone="accent">Read from the web · {pages.length}</SectionLabel>
            {pages.length === 0 ? (
              <p className="m-0 text-sm text-muted">No page evidence matches these filters.</p>
            ) : (
              <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(min(100%,360px),1fr))]">
                {pages.map((r) => (
                  <ResourceCard key={r.id} r={r} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </PageShell>
  );
}
