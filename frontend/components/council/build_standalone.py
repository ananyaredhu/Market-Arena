"""Build a self-contained HTML fixture page (no Node required).

    python build_standalone.py
then open council_standalone.html in a browser.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSS = (HERE / "council.css").read_text()


def load(name: str):
    return json.loads((HERE / "fixtures" / name).read_text())


def main() -> None:
    data = {
        "saas": {"council": load("council_saas.json"), "kit": load("kit_saas.json")},
        "cafe": {"council": load("council_cafe.json"), "kit": load("kit_cafe.json")},
    }
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Market Arena — CouncilPanel fixture</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet" />
<style>
{CSS}
body {{ margin: 0; background: #f5f5f4; }}
main {{ padding: 1.5rem; }}
.toolbar {{ display:flex; gap:.5rem; align-items:center; margin-bottom:1rem; flex-wrap:wrap; }}
#status {{ color:#78716c; font-size:.9rem; }}
</style>
</head>
<body>
<main>
  <div class="toolbar">
    <strong>Council fixture page (standalone)</strong>
    <button type="button" class="ma-btn" id="btn-saas">SaaS</button>
    <button type="button" class="ma-btn" id="btn-cafe">Café</button>
    <button type="button" class="ma-btn" id="btn-copy-md">Copy Markdown export</button>
    <button type="button" class="ma-btn" id="btn-download">Download .md</button>
    <span id="status"></span>
  </div>
  <div id="root"></div>
</main>
<script>
const DATA = {json.dumps(data)};
let pack = "saas";

function fragilityLabel(score) {{
  if (score < 0.25) return "Relatively robust to the tested ±20% prior shifts.";
  if (score < 0.5) return "Moderately sensitive to the tested prior shifts.";
  return "Fragile under the tested prior shifts — treat as a prompt for real experiments.";
}}
function confidenceTone(level) {{
  return level === "high" ? "#15803d" : level === "medium" ? "#b45309" : "#b91c1c";
}}
async function copyText(text) {{
  try {{ await navigator.clipboard.writeText(text); return true; }}
  catch (e) {{
    const a = document.createElement("textarea");
    a.value = text; document.body.appendChild(a); a.select();
    const ok = document.execCommand("copy"); document.body.removeChild(a); return ok;
  }}
}}
function buildMarkdown(council, kit) {{
  const lines = [
    `# Council verdict (${{council.run_id}})`, "", council.verdict, "",
    `Confidence: **${{council.confidence}}** · Fragility: **${{council.fragility.toFixed(2)}}**`,
    "", "## Risks", ...council.risks.map(r => `- **${{r.title}}** — ${{r.metric}}`),
    "", "## Experiments",
    ...council.experiments.map(e => `- **${{e.title}}** (${{e.kind}}): ${{e.hypothesis}} — ${{e.pass_threshold}}`),
  ];
  if (kit) {{
    lines.push("", "## Hypotheses", ...kit.hypotheses.map(h => `- ${{h}}`));
    lines.push("", "## Landing copy", "", kit.assets.landing_copy);
    lines.push("", "## Survey", ...kit.assets.survey.map((q,i) => `${{i+1}}. ${{q}}`));
    lines.push("", "## Interview", ...kit.assets.interview_script.map(q => `- ${{q}}`));
    lines.push("", "## Ads", ...kit.assets.ad_variants.map(a => `- ${{a}}`));
    lines.push("", "## Flyer", "", kit.assets.offline.flyer);
    lines.push("", "## Telegram", ...kit.assets.telegram_variants.map(t => `- ${{t}}`));
  }}
  return lines.join("\\n");
}}
function esc(s) {{
  return String(s).replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c]));
}}
function list(items) {{
  return items.length ? `<ul>${{items.map(i => `<li>${{esc(i)}}</li>`).join("")}}</ul>` : `<p class="ma-muted">None</p>`;
}}
function render() {{
  const {{ council, kit }} = DATA[pack];
  const reaction = council.competitor_reaction;
  const root = document.getElementById("root");
  root.innerHTML = `
  <section class="ma-council" data-testid="council-panel">
    <header class="ma-verdict-card">
      <div class="ma-verdict-top">
        <h2>Council verdict</h2>
        <span class="ma-pill" style="background:${{confidenceTone(council.confidence)}}">${{esc(council.confidence)}} confidence</span>
      </div>
      <p class="ma-verdict">${{esc(council.verdict)}}</p>
      <div class="ma-fragility">
        <div class="ma-fragility-bar"><div style="width:${{Math.round(council.fragility*100)}}%"></div></div>
        <p>Fragility <strong>${{council.fragility.toFixed(2)}}</strong> — ${{fragilityLabel(council.fragility)}}</p>
        <p class="ma-muted">Fragility measures sensitivity of the <em>simulation</em> to ±20% prior shifts. It is not a sales forecast.</p>
      </div>
      ${{council.engine_source === "mock" ? `<p class="ma-warn-banner">Engine source: mock adapter. Numbers are labelled mock results.</p>` : ""}}
      <div class="ma-actions">
        <button type="button" class="ma-btn" id="copy-verdict">Copy verdict</button>
      </div>
    </header>
    <div class="ma-grid">
      <div><h3>Who buys</h3>${{list(council.who_buys)}}</div>
      <div><h3>Who rejects</h3>${{list(council.who_rejects)}}</div>
    </div>
    <section>
      <h3>Top risks</h3>
      <ol class="ma-risks">${{council.risks.map(r => `<li><strong>${{esc(r.title)}}</strong><div class="ma-metric">${{esc(r.metric)}}</div><p class="ma-muted">${{esc(r.evidence)}}</p></li>`).join("")}}</ol>
      ${{reaction ? `<p class="ma-reaction">Likely competitor reaction: <code>${{esc(reaction.competitor_id)}}</code> → <code>${{esc(reaction.move)}}</code> (effect ${{reaction.effect_on_share}})</p>` : ""}}
    </section>
    <section>
      <h3>Recommended experiments</h3>
      <ul class="ma-experiments">${{council.experiments.map(e => `<li><div class="ma-exp-head"><strong>${{esc(e.title)}}</strong><span class="ma-kind">${{esc(e.kind)}}</span></div><p>${{esc(e.hypothesis)}}</p><p class="ma-muted">${{esc(e.pass_threshold)}}</p></li>`).join("")}}</ul>
    </section>
    <section>
      <h3>Experiment Kit</h3>
      <h4>Hypotheses</h4>${{list(kit.hypotheses)}}
      <div class="ma-tabs" id="tabs">
        ${{["landing","survey","interview","ads","offline","telegram","tracking"].map(t => `<button type="button" class="ma-tab" data-tab="${{t}}">${{t}}</button>`).join("")}}
      </div>
      <div class="ma-tab-panel" id="tab-panel"></div>
    </section>
  </section>`;
  document.getElementById("copy-verdict").onclick = async () => {{
    const ok = await copyText(council.verdict);
    document.getElementById("status").textContent = ok ? "Verdict copied." : "Copy failed.";
  }};
  const tabs = root.querySelectorAll("[data-tab]");
  const show = (name) => {{
    tabs.forEach(b => b.classList.toggle("ma-tab-active", b.dataset.tab === name));
    const a = kit.assets;
    let html = "";
    if (name === "landing") html = `<button class="ma-btn" id="copy-tab">Copy</button><pre class="ma-pre">${{esc(a.landing_copy)}}</pre>`;
    if (name === "survey") html = `<ol>${{a.survey.map(q => `<li>${{esc(q)}}</li>`).join("")}}</ol>`;
    if (name === "interview") html = `<ol>${{a.interview_script.map(q => `<li>${{esc(q)}}</li>`).join("")}}</ol>`;
    if (name === "ads") html = list(a.ad_variants);
    if (name === "offline") html = `<pre class="ma-pre">${{esc(a.offline.flyer)}}</pre><h4>Checklist</h4>${{list(a.offline.checklist)}}${{a.offline.price_board_test?.length ? `<h4>Price-board</h4>${{list(a.offline.price_board_test)}}` : ""}}`;
    if (name === "telegram") html = list(a.telegram_variants);
    if (name === "tracking" && a.tracking_plan) html = `${{list(a.tracking_plan.metrics)}}<p>${{esc(a.tracking_plan.decision_rule)}}</p>`;
    document.getElementById("tab-panel").innerHTML = html;
    const copyBtn = document.getElementById("copy-tab");
    if (copyBtn) copyBtn.onclick = async () => {{
      const ok = await copyText(a.landing_copy);
      document.getElementById("status").textContent = ok ? "Landing copy copied." : "Copy failed.";
    }};
  }};
  tabs.forEach(b => b.onclick = () => show(b.dataset.tab));
  show("landing");
  window.__councilMarkdown = () => buildMarkdown(council, kit);
  // Self-check for automated smoke without a browser automation stack.
  window.__councilSmoke = () => {{
    const panel = document.querySelector("[data-testid=council-panel]");
    const checks = {{
      panel: !!panel,
      verdict: !!council.verdict,
      risks: council.risks.length > 0,
      experiments: council.experiments.length > 0,
      kitHypotheses: kit.hypotheses.length >= 3,
      markdown: buildMarkdown(council, kit).includes(council.run_id),
    }};
    return checks;
  }};
}}
document.getElementById("btn-saas").onclick = () => {{ pack = "saas"; render(); document.getElementById("status").textContent = "Pack: saas"; }};
document.getElementById("btn-cafe").onclick = () => {{ pack = "cafe"; render(); document.getElementById("status").textContent = "Pack: cafe"; }};
document.getElementById("btn-copy-md").onclick = async () => {{
  const ok = await copyText(window.__councilMarkdown());
  document.getElementById("status").textContent = ok ? "Markdown copied." : "Copy failed.";
}};
document.getElementById("btn-download").onclick = () => {{
  const md = window.__councilMarkdown();
  const a = document.createElement("a");
  a.href = "data:text/markdown;charset=utf-8," + encodeURIComponent(md);
  a.download = DATA[pack].council.run_id + "-council.md";
  a.click();
  document.getElementById("status").textContent = "Download started.";
}};
render();
</script>
</body>
</html>
"""
    out = HERE / "council_standalone.html"
    out.write_text(html)
    print("wrote", out)


if __name__ == "__main__":
    main()
