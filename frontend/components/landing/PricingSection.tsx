import styles from "./landing-styles";

export default function PricingSection() {
  return (
    <section id="pricing" className={styles.wrap}>
      <div className={styles.sectionLabel}>{"} Pilot pricing · to be validated"}</div>
      <h2 className={styles.sectionTitle}>Start free. Pay when it earns it.</h2>
      <div className={styles.plans}>
        <article className={`${styles.lift} ${styles.plan}`}>
          <div className={styles.lbl}>Free</div>
          <div className={styles.price}>S$0</div>
          <ul className={styles.planList}>
            <li>3 simulations / month</li>
            <li>1 industry pack</li>
            <li>200 agents</li>
          </ul>
        </article>
        <article className={`${styles.lift} ${styles.planFeatured}`}>
          <div className={styles.planHead}>
            <span className={styles.planNameAccent}>Founder</span>
            <span className={styles.badge}>Recommended</span>
          </div>
          <div className={styles.price}>
            S$19<span className={styles.priceUnit}> /mo</span>
          </div>
          <ul className={styles.planListStrong}>
            <li>30 simulations / month</li>
            <li>All packs, 1,000 agents</li>
            <li>Scenario compare + Experiment Kit</li>
            <li>Telegram (1 bot)</li>
          </ul>
        </article>
        <article className={`${styles.lift} ${styles.plan}`}>
          <div className={styles.lbl}>Incubator</div>
          <div className={styles.price}>
            S$299<span className={styles.priceUnit}>+</span>
          </div>
          <ul className={styles.planList}>
            <li>Multi-project cohort dashboard</li>
            <li>Branded reports</li>
            <li>Calibration with uploaded data</li>
          </ul>
        </article>
      </div>
    </section>
  );
}
