import styles from "./landing-styles";

export default function BuiltDifferent() {
  return (
    <section className={styles.wrap}>
      <div className={styles.sectionLabel}>{"} Built different"}</div>
      <h2 className={styles.sectionTitle}>Not another AI that tells you your idea is great.</h2>
      <div className={styles.bento}>
        <div className={`${styles.lift} ${styles.statWide}`}>
          <div className={styles.statZero}>0</div>
          <div className={styles.statCopyWide}>purchase decisions made by a language model. A transparent utility model decides; the LLM only explains.</div>
        </div>
        <div className={`${styles.lift} ${styles.statCard}`}>
          <div className={styles.statTeal}>1,000</div>
          <div className={styles.statCopy}>customers scored in under a second, so every slider re-runs instantly.</div>
        </div>
        <div className={`${styles.lift} ${styles.statCard}`}>
          <div className={styles.statViolet}>p10–90</div>
          <div className={styles.statCopy}>a range on every result. We show uncertainty instead of hiding it.</div>
        </div>
      </div>
    </section>
  );
}
