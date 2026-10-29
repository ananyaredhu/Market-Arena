import styles from "./landing-styles";

export default function FeatureShowcases() {
  return (
    <section id="features" className={styles.wrap}>
      <div className={styles.sectionLabel}>{"} Inside the workbench"}</div>
      <h2 className={`${styles.sectionTitle} ${styles.featureTitle}`}>Everything a founder needs to decide what to test next.</h2>
      <div className={styles.features}>
        <article className={`${styles.lift} ${styles.featureWide} ${styles.glassCard}`}>
          <div className={styles.featureLabelBlue}>Glass-Box inspector</div>
          <h3 className={styles.featureHeading}>See why every customer chose, and overrule it.</h3>
          <p className={styles.featureCopy}>Utility breakdown, plain-language reason, and the smallest change that would flip the decision. Overrides stay in the audit trail.</p>
          <div className={styles.utility} aria-hidden="true">
            <div className={styles.utilityRow}>
              <span className={styles.utilityName}>Price</span>
              <div className={styles.utilityTrack}><div className={`${styles.utilityFill} ${styles.fillBlue}`} /></div>
              <span className={styles.utilityScore}>+2.2</span>
            </div>
            <div className={styles.utilityRow}>
              <span className={styles.utilityName}>Features</span>
              <div className={styles.utilityTrack}><div className={`${styles.utilityFill} ${styles.fillLime}`} /></div>
              <span className={styles.utilityScore}>−0.9</span>
            </div>
            <div className={styles.utilityRow}>
              <span className={styles.utilityName}>Brand</span>
              <div className={styles.utilityTrack}><div className={`${styles.utilityFill} ${styles.fillBlueShort}`} /></div>
              <span className={styles.utilityScore}>+0.7</span>
            </div>
          </div>
        </article>
        <article className={`${styles.lift} ${styles.feature} ${styles.councilCard}`}>
          <div className={styles.featureLabelAmber}>Arena Council</div>
          <h3 className={styles.featureHeading}>A verdict with a fragility score.</h3>
          <p className={styles.featureCopy}>Rival strategist, devil’s advocate and moderator, each grounded in engine numbers.</p>
          <div className={styles.fragility} aria-hidden="true"><div className={styles.needle} /></div>
          <div className={styles.fragilityLabels}><span>robust</span><span>fragile</span></div>
        </article>
        <article className={`${styles.lift} ${styles.feature} ${styles.scenarioCard}`}>
          <div className={styles.featureLabelTeal}>Scenario lab</div>
          <h3 className={styles.featureHeading}>Change one thing, compare two markets.</h3>
          <p className={styles.featureCopy}>Price, features, rival moves. Side by side, split by segment.</p>
          <div className={styles.scenarioMix} aria-hidden="true">
            <div className={styles.mixCoral} />
            <div className={styles.mixTeal} />
            <div className={styles.mixAmber} />
            <div className={styles.mixViolet} />
          </div>
        </article>
        <article className={`${styles.lift} ${styles.featureWide} ${styles.kitCard}`}>
          <div className={styles.kitCopy}>
            <div className={styles.featureLabelViolet}>Experiment Kit + Telegram</div>
            <h3 className={styles.featureHeading}>Close the loop with real evidence.</h3>
            <p className={styles.featureCopy}>Hypotheses with pass thresholds, landing copy, scripts, and an approval-gated A/B send to your own opted-in list.</p>
          </div>
          <div className={styles.kitThread} aria-hidden="true">
            <div className={`${styles.chat} ${styles.pop1}`}>Save hours every week.</div>
            <div className={`${styles.chat} ${styles.pop2}`}>Never fall behind again.</div>
            <div className={`${styles.chatWin} ${styles.pop3}`}>B wins · 11.5% taps</div>
          </div>
        </article>
      </div>
    </section>
  );
}
