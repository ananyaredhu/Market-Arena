"use client";
// Standalone page so Person C can build the Arena without anyone else's code.
import { useEffect, useState } from "react";

import Arena from "@/components/arena/Arena";
import { api } from "@/lib/api";
import type { RunResult } from "@/lib/types";

export default function DevArena() {
  const [run, setRun] = useState<RunResult | null>(null);
  useEffect(() => {
    api<RunResult>("/runs/run_42").then(setRun);
  }, []);
  if (!run) return <main className="p-8 text-muted">Loading…</main>;
  return (
    <main className="flex min-h-screen">
      <Arena runResult={run} onAgentClick={(id) => console.log("agent clicked", id)} />
    </main>
  );
}
