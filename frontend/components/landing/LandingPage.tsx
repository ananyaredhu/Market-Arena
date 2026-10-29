import ArenaPreview from "./ArenaPreview";
import BuiltDifferent from "./BuiltDifferent";
import FeatureShowcases from "./FeatureShowcases";
import FinalCta from "./FinalCta";
import HeroBackdrop from "./HeroBackdrop";
import HeroCopy from "./HeroCopy";
import HowItWorks from "./HowItWorks";
import LandingHeader from "./LandingHeader";
import PhilosophyBand from "./PhilosophyBand";
import PricingSection from "./PricingSection";
import PrinciplesStrip from "./PrinciplesStrip";
import styles from "./landing-styles";

export default function LandingPage() {
  return (
    <main className={styles.page}>
      <HeroBackdrop>
        <LandingHeader />
        <HeroCopy />
        <ArenaPreview />
      </HeroBackdrop>
      <PrinciplesStrip />
      <BuiltDifferent />
      <HowItWorks />
      <FeatureShowcases />
      <PhilosophyBand />
      <PricingSection />
      <FinalCta />
    </main>
  );
}
