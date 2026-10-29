import styles from "./landing-styles";

const PHRASES = [
  { text: "Math decides, language explains", muted: false },
  { text: "Every dot is traceable", muted: true },
  { text: "Overrule any agent", muted: false },
  { text: "Ranges, never promises", muted: true },
];

function PhraseRun({ hidden = false }: { hidden?: boolean }) {
  return (
    <span aria-hidden={hidden || undefined}>
      {PHRASES.map((phrase) => (
        <span key={`${phrase.text}-${hidden ? "copy" : "orig"}`}>
          <span className={phrase.muted ? `${styles.phrase} ${styles.phraseMuted}` : styles.phrase}>{phrase.text}</span>
          <span className={styles.star}>✦</span>
        </span>
      ))}
    </span>
  );
}

export default function PrinciplesStrip() {
  return (
    <section className={styles.principles} aria-label="Principles">
      <div className={styles.marquee}>
        <PhraseRun />
        <span className={styles.marqueeDuplicate}>
          <PhraseRun hidden />
        </span>
      </div>
    </section>
  );
}
