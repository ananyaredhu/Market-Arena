import type { ReactNode } from "react";

import styles from "./landing-styles";

export default function HeroBackdrop({ children }: { children: ReactNode }) {
  return (
    <section className={styles.heroSection}>
      <div className={`${styles.glow} ${styles.glowLime}`} aria-hidden="true" />
      <div className={`${styles.glow} ${styles.glowViolet}`} aria-hidden="true" />
      <div className={`${styles.glow} ${styles.glowTeal}`} aria-hidden="true" />
      <svg className={styles.orbit} aria-hidden="true" viewBox="0 0 1600 1600">
        <ellipse cx="800" cy="800" rx="780" ry="420" fill="none" stroke="#C8F560" strokeOpacity="0.35" strokeWidth="1" />
        <ellipse cx="800" cy="800" rx="640" ry="300" fill="none" stroke="#fff" strokeOpacity="0.18" strokeWidth="1" transform="rotate(35 800 800)" />
        <circle cx="1580" cy="800" r="5" fill="#C8F560" />
      </svg>
      <svg className={styles.orbitReverse} aria-hidden="true" viewBox="0 0 1600 1600">
        <ellipse cx="800" cy="800" rx="520" ry="520" fill="none" stroke="#A98BFF" strokeOpacity="0.4" strokeWidth="1" strokeDasharray="3 9" />
        <circle cx="800" cy="280" r="5" fill="#34D3BE" />
      </svg>
      {children}
    </section>
  );
}
