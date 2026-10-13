import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Self-hosted (Latin subset, variable weight) so the app and the offline demo never need Google Fonts.
// Source: the fonts embedded in "Market Arena UI Ideas". Bricolage Grotesque, DM Sans and JetBrains Mono
// are all open-licence (SIL OFL).
const bricolage = localFont({ src: "./fonts/BricolageGrotesque-latin.woff2", variable: "--font-bricolage", weight: "500 700" });
const dmSans = localFont({ src: "./fonts/DMSans-latin.woff2", variable: "--font-dm-sans", weight: "400 700" });
const jetbrains = localFont({ src: "./fonts/JetBrainsMono-latin.woff2", variable: "--font-jetbrains", weight: "400 500" });

export const metadata: Metadata = {
  title: "Market Arena",
  description: "Test your startup against a simulated market.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${bricolage.variable} ${dmSans.variable} ${jetbrains.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
