"use client";
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main id="main" className="wrap error-page"><p className="eyebrow coral">A SMALL HICCUP</p><h1>Let’s try<br /><em>that again.</em></h1><p>This page did not load correctly. Your download does not require an account or payment.</p><button className="button" type="button" onClick={reset}>Try again <span aria-hidden="true">↻</span></button></main>;
}
