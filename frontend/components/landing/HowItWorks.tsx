import styles from "./landing-styles";

const DOTS = ["#FF7A6B", "#34D3BE", "#F6B93B", "#A98BFF", "#34D3BE", "#FF7A6B"];

export default function HowItWorks() {
  return (
    <section id="how" className={styles.wrap}>
      <div className={styles.sectionLabel}>{"} How it works"}</div>
      <h2 className={`${styles.sectionTitle} ${styles.stepsTitle}`}>From idea to evidence in four moves.</h2>
      <div className={styles.timeline} aria-hidden="true">
        <div className={styles.timelineSweep} />
      </div>
      <div className={styles.steps}>
        <article className={`${styles.lift} ${styles.step}`}>
          <div className={styles.stepIndex}>01</div>
          <div className={styles.stepTitle}>Describe</div>
          <p className={styles.stepCopy}>Paste your idea. We extract the product, flag missing assumptions and pick an industry pack.</p>
          <div className={styles.bars} aria-hidden="true">
            <div className={`${styles.bar} ${styles.barWide}`} />
            <div className={`${styles.bar} ${styles.barMid}`} />
            <div className={`${styles.bar} ${styles.barAccent}`} />
          </div>
        </article>
        <article className={`${styles.lift} ${styles.step}`}>
          <div className={styles.stepIndex}>02</div>
          <div className={styles.stepTitle}>Simulate</div>
          <p className={styles.stepCopy}>Hundreds of customers with budgets, priorities and habits choose between you, rivals and doing nothing.</p>
          <div className={styles.stepDots} aria-hidden="true">
            {DOTS.map((color, index) => (
              <span key={index} className={styles.stepDot} style={{ background: color, boxShadow: `0 0 10px ${color}` }} />
            ))}
          </div>
        </article>
        <article className={`${styles.lift} ${styles.step}`}>
          <div className={styles.stepIndex}>03</div>
          <div className={styles.stepTitle}>Interrogate</div>
          <p className={styles.stepCopy}>Click any dot to see why it chose, what would flip it, and overrule it. Then ask the Council.</p>
          <div className={styles.bars} aria-hidden="true">
            <div className={`${styles.bar} ${styles.barBlue}`} />
            <div className={`${styles.bar} ${styles.barShort}`} />
          </div>
        </article>
        <article className={`${styles.lift} ${styles.step}`}>
          <div className={styles.stepIndex}>04</div>
          <div className={styles.stepTitle}>Test for real</div>
          <p className={styles.stepCopy}>Get landing copy, a survey, interview scripts and a Telegram A/B test to check the simulation against reality.</p>
          <div className={styles.stepBubble}>Never fall behind again.</div>
        </article>
      </div>
    </section>
  );
}
