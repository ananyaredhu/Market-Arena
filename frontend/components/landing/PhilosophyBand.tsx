import styles from "./landing-styles";

export default function PhilosophyBand() {
  return (
    <section className={styles.wrap}>
      <div className={styles.honest}>
        <h2 className={styles.honestTitle}>
          We don’t predict your revenue. We tell you <span className={styles.honestAccent}>what to test next.</span>
        </h2>
        <div className={styles.rangeChart} aria-hidden="true">
          <div className={styles.rangeBase} />
          <div className={styles.rangeBand} />
          <div className={styles.rangeNeedle} />
          <div className={`${styles.rangeTick} ${styles.tickLow}`}>p10</div>
          <div className={`${styles.rangeTick} ${styles.tickHigh}`}>p90</div>
        </div>
      </div>
    </section>
  );
}
