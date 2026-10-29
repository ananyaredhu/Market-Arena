import Link from "next/link";

import styles from "./landing-styles";

export default function HeroCopy() {
  return (
    <div id="top" className={styles.heroCopy}>
      <div className={`${styles.statusPill} ${styles.rise1}`}>
        <span className={styles.statusDot} aria-hidden="true" />
        <span className={styles.statusText}>Live simulation · 240 customers · seed 42</span>
      </div>
      <h1 className={`${styles.heroTitle} ${styles.rise2}`}>
        Test your startup against a market that <span className={styles.shine}>fights back.</span>
      </h1>
      <p className={`${styles.heroLead} ${styles.rise3}`}>
        Market Arena simulates hundreds of customers and your rivals. Change your price, watch the market move, click any customer to see exactly why, then run the real experiment.
      </p>
      <div className={`${styles.heroActions} ${styles.rise4}`}>
        <Link className={`${styles.btn} ${styles.heroPrimary}`} href="/intake">
          Run a free simulation <span aria-hidden="true">→</span>
        </Link>
        <a className={`${styles.btn} ${styles.ghost} ${styles.heroGhost}`} href="#how">
          See how it works
        </a>
      </div>
      <div className={styles.disclaimer}>Simulated outcome under stated assumptions · every result shown as a range</div>
    </div>
  );
}
