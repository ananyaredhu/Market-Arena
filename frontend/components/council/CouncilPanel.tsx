"use client";

/**
 * Person B: CouncilPanel.
 * Accepts council + kit props and works on fixtures with no API.
 * Design tokens are local CSS variables so this does not depend on a shared theme yet.
 */
import { useMemo, useState } from "react";
import type { CouncilOutput, CouncilPanelProps, KitOutput } from "./types";
import "./council.css";

type TabId = "landing" | "survey" | "interview" | "ads" | "offline" | "telegram" | "tracking";

const TABS: { id: TabId; label: string }[] = [
  { id: "landing", label: "Landing" },
  { id: "survey", label: "Survey" },
  { id: "interview", label: "Interview" },
  { id: "ads", label: "Ads" },
  { id: "offline", label: "Offline" },
  { id: "telegram", label: "Telegram" },
  { id: "tracking", label: "Tracking" },
];

function fragilityLabel(score: number): string {
  if (score < 0.25) return "Relatively robust to the tested ±20% prior shifts.";
  if (score < 0.5) return "Moderately sensitive to the tested prior shifts.";
  return "Fragile under the tested prior shifts — treat as a prompt for real experiments.";
}

function confidenceTone(level: string): string {
  if (level === "high") return "var(--ma-ok)";
  if (level === "medium") return "var(--ma-warn)";
  return "var(--ma-bad)";
}

async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall through */
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.select();
  const ok = document.execCommand("copy");
  document.body.removeChild(area);
  return ok;
}

function buildMarkdown(council: CouncilOutput, kit: KitOutput | null | undefined): string {
  const lines: string[] = [
    `# Council verdict (${council.run_id})`,
    "",
    council.verdict,
    "",
    `Confidence: **${council.confidence}** · Fragility: **${council.fragility.toFixed(2)}**`,
    "",
    "## Risks",
    ...council.risks.map((r) => `- **${r.title}** — ${r.metric}`),
    "",
    "## Experiments",
    ...council.experiments.map(
      (e) => `- **${e.title}** (${e.kind}): ${e.hypothesis} — ${e.pass_threshold}`
    ),
  ];
  if (kit) {
    lines.push("", "## Hypotheses", ...kit.hypotheses.map((h) => `- ${h}`));
    lines.push("", "## Landing copy", "", kit.assets.landing_copy);
    lines.push("", "## Survey", ...kit.assets.survey.map((q, i) => `${i + 1}. ${q}`));
    lines.push("", "## Interview script", ...kit.assets.interview_script.map((q) => `- ${q}`));
    lines.push("", "## Ad variants", ...kit.assets.ad_variants.map((a) => `- ${a}`));
    lines.push("", "## Offline flyer", "", kit.assets.offline.flyer);
    lines.push("", "## Offline checklist", ...kit.assets.offline.checklist.map((c) => `- ${c}`));
    if (kit.assets.offline.price_board_test?.length) {
      lines.push("", "## Price-board test", ...kit.assets.offline.price_board_test.map((c) => `- ${c}`));
    }
    lines.push("", "## Telegram variants", ...kit.assets.telegram_variants.map((t) => `- ${t}`));
    if (kit.assets.tracking_plan) {
      lines.push("", "## Tracking plan");
      lines.push(...kit.assets.tracking_plan.metrics.map((m) => `- ${m}`));
      lines.push("", kit.assets.tracking_plan.decision_rule);
    }
  }
  if (council.limitations?.length) {
    lines.push("", "## Limitations", ...council.limitations.map((l) => `- ${l}`));
  }
  return lines.join("\n");
}

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [state, setState] = useState<"idle" | "ok" | "err">("idle");
  return (
    <button
      type="button"
      className="ma-btn"
      onClick={async () => {
        const ok = await copyText(text);
        setState(ok ? "ok" : "err");
        window.setTimeout(() => setState("idle"), 1500);
      }}
    >
      {state === "ok" ? "Copied" : state === "err" ? "Copy failed" : label}
    </button>
  );
}

function isCouncil(value: unknown): value is CouncilOutput {
  return !!value && typeof value === "object" && "verdict" in (value as object) && "risks" in (value as object);
}

export function CouncilPanel({ council, kit, loading = false, error = null }: CouncilPanelProps) {
  const [tab, setTab] = useState<TabId>("landing");
  const markdown = useMemo(
    () => (isCouncil(council) ? buildMarkdown(council, kit) : ""),
    [council, kit]
  );

  if (loading) {
    return (
      <section className="ma-council" aria-busy="true">
        <p className="ma-muted">Loading council and experiment kit…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="ma-council">
        <p className="ma-error" role="alert">
          {error}
        </p>
      </section>
    );
  }

  if (!isCouncil(council)) {
    return (
      <section className="ma-council">
        <p className="ma-muted">No council output yet. Pass fixture data or wait for a run.</p>
      </section>
    );
  }

  const reaction = council.competitor_reaction;
  const assets = kit?.assets;

  return (
    <section className="ma-council" data-testid="council-panel">
      <header className="ma-verdict-card">
        <div className="ma-verdict-top">
          <h2>Council verdict</h2>
          <span className="ma-pill" style={{ background: confidenceTone(council.confidence) }}>
            {council.confidence} confidence
          </span>
        </div>
        <p className="ma-verdict">{council.verdict}</p>
        <div className="ma-fragility">
          <div className="ma-fragility-bar" aria-hidden="true">
            <div style={{ width: `${Math.round(council.fragility * 100)}%` }} />
          </div>
          <p>
            Fragility <strong>{council.fragility.toFixed(2)}</strong> — {fragilityLabel(council.fragility)}
          </p>
          <p className="ma-muted">
            Fragility measures sensitivity of the <em>simulation</em> to ±20% prior shifts. It is not a
            statistical confidence interval and not a sales forecast.
          </p>
        </div>
        {council.engine_source === "mock" && (
          <p className="ma-warn-banner">Engine source: mock adapter. Numbers are labelled mock results.</p>
        )}
        <div className="ma-actions">
          <CopyButton text={council.verdict} label="Copy verdict" />
          {markdown && <CopyButton text={markdown} label="Copy Markdown export" />}
          {markdown && (
            <a
              className="ma-btn ma-btn-link"
              download={`${council.run_id}-council.md`}
              href={`data:text/markdown;charset=utf-8,${encodeURIComponent(markdown)}`}
            >
              Download .md
            </a>
          )}
        </div>
      </header>

      <div className="ma-grid">
        <div>
          <h3>Who buys</h3>
          {council.who_buys.length ? (
            <ul>{council.who_buys.map((line) => <li key={line}>{line}</li>)}</ul>
          ) : (
            <p className="ma-muted">No buyer segments in the input choices.</p>
          )}
        </div>
        <div>
          <h3>Who rejects</h3>
          {council.who_rejects.length ? (
            <ul>{council.who_rejects.map((line) => <li key={line}>{line}</li>)}</ul>
          ) : (
            <p className="ma-muted">No rejector segments in the input choices.</p>
          )}
        </div>
      </div>

      <section>
        <h3>Top risks</h3>
        {council.risks.length ? (
          <ol className="ma-risks">
            {council.risks.map((risk) => (
              <li key={risk.title}>
                <strong>{risk.title}</strong>
                <div className="ma-metric">{risk.metric}</div>
                <p className="ma-muted">{risk.evidence}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="ma-muted">No ranked risks from the available sensitivity tests.</p>
        )}
        {reaction && (
          <p className="ma-reaction">
            Likely competitor reaction: <code>{reaction.competitor_id}</code> → <code>{reaction.move}</code>{" "}
            (effect on our share {reaction.effect_on_share >= 0 ? "+" : ""}
            {reaction.effect_on_share.toFixed(4)})
          </p>
        )}
      </section>

      <section>
        <h3>Recommended experiments</h3>
        {council.experiments.length ? (
          <ul className="ma-experiments">
            {council.experiments.map((exp) => (
              <li key={exp.title}>
                <div className="ma-exp-head">
                  <strong>{exp.title}</strong>
                  <span className="ma-kind">{exp.kind}</span>
                </div>
                <p>{exp.hypothesis}</p>
                <p className="ma-muted">{exp.pass_threshold}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="ma-muted">No experiments generated.</p>
        )}
      </section>

      <section>
        <div className="ma-kit-head">
          <h3>Experiment Kit</h3>
          {!kit && <p className="ma-muted">No kit data provided.</p>}
        </div>
        {kit && (
          <>
            <h4>Hypotheses</h4>
            <ul>
              {kit.hypotheses.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
            <div className="ma-tabs" role="tablist">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={tab === t.id}
                  className={tab === t.id ? "ma-tab ma-tab-active" : "ma-tab"}
                  onClick={() => setTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="ma-tab-panel" role="tabpanel">
              {tab === "landing" && assets && (
                <>
                  <CopyButton text={assets.landing_copy} />
                  <pre className="ma-pre">{assets.landing_copy}</pre>
                </>
              )}
              {tab === "survey" && assets && (
                <>
                  <CopyButton text={assets.survey.map((q, i) => `${i + 1}. ${q}`).join("\n")} />
                  <ol>{assets.survey.map((q) => <li key={q}>{q}</li>)}</ol>
                </>
              )}
              {tab === "interview" && assets && (
                <>
                  <CopyButton text={assets.interview_script.join("\n")} />
                  <ol>{assets.interview_script.map((q) => <li key={q}>{q}</li>)}</ol>
                </>
              )}
              {tab === "ads" && assets && (
                <>
                  <CopyButton text={assets.ad_variants.join("\n\n")} />
                  <ul>{assets.ad_variants.map((a) => <li key={a}>{a}</li>)}</ul>
                </>
              )}
              {tab === "offline" && assets && (
                <>
                  <CopyButton
                    text={[
                      assets.offline.flyer,
                      "",
                      "Checklist:",
                      ...assets.offline.checklist.map((c) => `- ${c}`),
                      "",
                      "Price-board test:",
                      ...(assets.offline.price_board_test || []).map((c) => `- ${c}`),
                    ].join("\n")}
                  />
                  <pre className="ma-pre">{assets.offline.flyer}</pre>
                  <h4>Checklist</h4>
                  <ul>{assets.offline.checklist.map((c) => <li key={c}>{c}</li>)}</ul>
                  {!!assets.offline.price_board_test?.length && (
                    <>
                      <h4>Price-board test</h4>
                      <ul>{assets.offline.price_board_test.map((c) => <li key={c}>{c}</li>)}</ul>
                    </>
                  )}
                </>
              )}
              {tab === "telegram" && assets && (
                <>
                  <CopyButton text={assets.telegram_variants.join("\n\n")} />
                  <ul>{assets.telegram_variants.map((t) => <li key={t}>{t}</li>)}</ul>
                </>
              )}
              {tab === "tracking" && assets && (
                assets.tracking_plan ? (
                  <>
                    <CopyButton
                      text={[
                        ...assets.tracking_plan.metrics.map((m) => `- ${m}`),
                        "",
                        assets.tracking_plan.decision_rule,
                      ].join("\n")}
                    />
                    <ul>{assets.tracking_plan.metrics.map((m) => <li key={m}>{m}</li>)}</ul>
                    <p>{assets.tracking_plan.decision_rule}</p>
                  </>
                ) : (
                  <p className="ma-muted">No tracking plan in this kit.</p>
                )
              )}
            </div>
          </>
        )}
      </section>

      {!!council.limitations?.length && (
        <details className="ma-limitations">
          <summary>Limitations and caveats</summary>
          <ul>{council.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
        </details>
      )}
    </section>
  );
}

export default CouncilPanel;
