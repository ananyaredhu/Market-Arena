import type { Metadata } from "next";

import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "Market Arena",
  description: "Test your startup against a market that fights back.",
};

export default function Home() {
  return <LandingPage />;
}
