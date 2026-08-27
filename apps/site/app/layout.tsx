import type { Metadata } from "next";
import { MotionController, SiteFooter, SiteHeader } from "./motion";
import "./globals.css";

const siteOrigin = process.env.NEXT_PUBLIC_SITE_URL || "https://project-hope-charities.vercel.app";
export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin),
  title: { default: "Project Hope — Less admin. More human.", template: "%s — Project Hope" },
  description: "A calmer workspace for charity contacts, volunteers, schedules, and reviewable writing assistance. Explore Project Hope and download the desktop preview directly.",
  icons: { icon: "/hope-mark.png", apple: "/hope-mark.png" },
  openGraph: { type: "website", siteName: "Project Hope", title: "Project Hope — Less admin. More human.", description: "A calmer workspace for charities. Download. Install. Explore.", images: [{ url: "/images/social-card.png", width: 1730, height: 909, alt: "Project Hope. Less admin. More human. A calmer workspace for charities." }] },
  twitter: { card: "summary_large_image", images: ["/images/social-card.png"] },
  robots: { index: true, follow: true },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><SiteHeader />{children}<SiteFooter /><MotionController /></body></html>;
}
