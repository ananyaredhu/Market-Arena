"use client";

import { useEffect, useMemo, useState } from "react";

import { buildCustomers, renderPreview, type ModeIndex } from "@/lib/landing-preview";

import styles from "./landing-styles";

export default function ArenaPreview() {
  const customers = useMemo(() => buildCustomers(), []);
  const [mode, setMode] = useState<ModeIndex>(1);
  const [cycle, setCycle] = useState(0);
  const preview = useMemo(() => renderPreview(customers, mode), [customers, mode]);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(() => {
      setMode((current) => ((current + 1) % 3) as ModeIndex);
    }, 4200);
    return () => window.clearInterval(timer);
  }, [cycle]);

  return (
    <div id="arena" className={styles.arenaWrap}>
      <div className={styles.arenaWindow}>
        <div className={styles.chrome}>
          <span className={styles.traffic} aria-hidden="true">
            <span style={{ background: "#FF7A6B" }} />
            <span style={{ background: "#F6B93B" }} />
            <span style={{ background: "#34D3BE" }} />
          </span>
          <span className={styles.chromeTitle}>StudyFlow · SaaS pack · run_8f21</span>
          <span className={styles.chromeLive}>● live</span>
        </div>
        <p className={styles.demoNote}>Illustrative preview · demo data, not a live simulation or a real market result.</p>
        <div className={styles.arenaBody}>
          <div className={styles.field}>
            <div className={styles.canvas} aria-hidden="true">
              {preview.bubbles.map((bubble) => (
                <div
                  key={bubble.label}
                  className={styles.bubble}
                  style={{
                    left: `${bubble.left}%`,
                    top: `${bubble.top}%`,
                    width: `${bubble.w}%`,
                    borderColor: bubble.stroke,
                    borderStyle: bubble.dash,
                    background: bubble.fill,
                    boxShadow: bubble.glow,
                  }}
                >
                  <div className={styles.bubbleLabel} style={{ color: bubble.stroke }}>
                    {bubble.label} <span className={styles.bubbleCount}>· {bubble.count}</span>
                  </div>
                </div>
              ))}
              {preview.dots.map((dot, index) => (
                <div
                  key={index}
                  className={styles.dot}
                  style={{ left: `${dot.x}%`, top: `${dot.y}%`, background: dot.c, boxShadow: dot.sh, zIndex: dot.z }}
                />
              ))}
              <div className={styles.heroDot} style={{ left: `${preview.hero.x}%`, top: `${preview.hero.y}%` }} />
            </div>
          </div>
          <aside className={styles.aside} aria-label="Illustrative StudyFlow preview">
            <div>
              <div id="preview-price" className={`${styles.lbl} ${styles.priceLabel}`}>Your price · per month</div>
              <div className={styles.pills} role="group" aria-labelledby="preview-price">
                {preview.pills.map((pill, index) => (
                  <button
                    key={pill.label}
                    type="button"
                    className={pill.on ? `${styles.pill} ${styles.pillOn}` : styles.pill}
                    aria-pressed={pill.on}
                    onClick={() => {
                      setMode(index as ModeIndex);
                      setCycle((value) => value + 1);
                    }}
                  >
                    {pill.label}
                  </button>
                ))}
              </div>
            </div>
            <div aria-live="polite">
              <div className={styles.lbl}>StudyFlow share</div>
              <div className={styles.shareRow}>
                <span className={styles.shareValue}>{preview.youPct}%</span>
                <span className={styles.delta} style={{ color: preview.deltaColor }}>{preview.deltaText}</span>
              </div>
              <div className={styles.range}>p10–p90: {preview.youRange}</div>
            </div>
            <div className={styles.rows}>
              {preview.rows.map((row) => (
                <div key={row.label} className={styles.row}>
                  <span className={styles.rowLabel}>{row.label}</span>
                  <div className={styles.track}>
                    <div className={styles.trackFill} style={{ width: `${row.bar}%`, background: row.stroke }} />
                  </div>
                  <span className={styles.rowPct}>{row.pct}%</span>
                </div>
              ))}
            </div>
            <div className={styles.glass}>
              <div className={styles.glassHead}>
                <span className={styles.glassTag}>Glass-Box · a17</span>
                <span className={styles.glassSwatch} aria-hidden="true" />
              </div>
              <div className={styles.glassBody}>
                Chose <b className={styles.glassChoice}>FreeTool</b>: the price gap outweighed AI planning.
              </div>
              <div className={styles.glassFlip}>would flip at −S$2.30</div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
