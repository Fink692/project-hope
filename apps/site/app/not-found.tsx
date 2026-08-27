import Link from "next/link";
export default function NotFound() {
  return <main id="main" className="wrap error-page"><p className="eyebrow coral">A SMALL DETOUR</p><h1>Let’s get you<br /><em>back home.</em></h1><p>That page or download is not available. Visit the download section for the current verified installers.</p><Link className="button" href="/#download">Back to downloads <span aria-hidden="true">↗</span></Link></main>;
}
