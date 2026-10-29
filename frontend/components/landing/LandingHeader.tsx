import Link from "next/link";

import styles from "./landing-styles";

function NavLinks({ className }: { className: string }) {
  return (
    <nav className={className} aria-label="Landing">
      <a href="#how">How it works<sup> 4</sup></a>
      <a href="#features">Features<sup> 4</sup></a>
      <a href="#pricing">Pricing<sup> 3</sup></a>
    </nav>
  );
}

export default function LandingHeader() {
  return (
    <header className={styles.header}>
      <a className={styles.brand} href="#top">
        <svg width="30" height="30" viewBox="0 0 28 28" aria-hidden="true">
          <circle cx="14" cy="14" r="12" fill="none" stroke="#C8F560" strokeWidth="2" />
          <circle cx="14" cy="14" r="6" fill="none" stroke="#7C8DB0" strokeWidth="2" />
          <circle cx="14" cy="14" r="2" fill="#C8F560" />
        </svg>
        <span className={styles.wordmark}>Market Arena</span>
      </a>
      <NavLinks className={styles.nav} />
      <details className={styles.mobileNav}>
        <summary>Menu</summary>
        <NavLinks className={styles.mobilePanel} />
      </details>
      <Link className={`${styles.btn} ${styles.headerCta}`} href="/intake">
        Run a simulation
      </Link>
    </header>
  );
}
