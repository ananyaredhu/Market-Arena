import Link from "next/link";

import styles from "./landing-styles";

export default function FinalCta() {
  return (
    <section className={styles.final}>
      <div className={`${styles.glow} ${styles.glowFinal}`} aria-hidden="true" />
      <div className={styles.finalInner}>
        <h2 className={styles.finalTitle}>Find out before you build.</h2>
        <Link className={`${styles.btn} ${styles.finalCta}`} href="/intake">
          Run a free simulation <span aria-hidden="true">→</span>
        </Link>
      </div>
      <footer className={styles.footer}>
        <span>© 2026 Market Arena</span>
        <span>Simulated outcomes under stated assumptions. Not financial advice.</span>
      </footer>
    </section>
  );
}
