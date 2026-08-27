import Image from "next/image";
import Link from "next/link";
import { Downloads, ProductTour } from "./product";
import { Questions, TiltSurface } from "./motion";
import { release } from "../lib/releases";

export default function Home() {
  return <main id="main">
    <section className="hero wrap">
      <div className="hero-copy">
        <p className="eyebrow hero-enter"><span className="live-dot" /> FOR PEOPLE MAKING A DIFFERENCE</p>
        <h1><span className="word-mask"><span>Less admin.</span></span><span className="word-mask"><em>More human.</em></span></h1>
        <p className="lede hero-enter delay-2">A calmer home for your charity’s everyday work. Bring your people, plans, and ideas together—with a little help when you need it.</p>
        <div className="hero-actions hero-enter delay-3"><a className="button" href="#download">Find your download <span aria-hidden="true">↓</span></a><a className="quiet-link" href="#inside">Take a closer look <span aria-hidden="true">↗</span></a></div>
        <p className="micro hero-enter delay-4">Desktop preview <span>·</span> Sample workspace included <span>·</span> No card</p>
        <div className="hero-note hero-enter delay-4"><span className="asterisk" aria-hidden="true">✳</span><p>Built around your mission.<br /><strong>Not another thing to manage.</strong></p></div>
      </div>
      <div className="hero-stage hero-enter delay-2">
        <div className="orbit orbit-one" aria-hidden="true" /><div className="orbit orbit-two" aria-hidden="true" />
        <div className="stage-spark spark-one" aria-hidden="true">✳</div><div className="stage-spark spark-two" aria-hidden="true">✳</div>
        <div data-parallax className="parallax-layer"><TiltSurface className="hero-visual">
          <div className="visual-top"><span>A LITTLE MORE TOGETHER.</span><span>01 / PROJECT HOPE</span></div>
          <div className="app-frame"><div className="window-bar" aria-hidden="true"><i /><i /><i /><span>Project Hope · sample workspace</span></div>
            <Image className="product-shot" src="/images/contacts.png" alt="The working Project Hope contact-import screen, with a spreadsheet preview, row checks, and review actions using fictional records." width={1440} height={1100} priority sizes="(max-width: 800px) 90vw, 48vw" />
          </div>
          <div className="visual-caption"><span className="caption-icon" aria-hidden="true">✓</span><div><strong>Your spreadsheet has a new home.</strong><p>Review. Bring it in. Get back to your people.</p></div><span aria-hidden="true">↗</span></div>
        </TiltSurface></div>
        <div className="floating-note note-top"><span className="tiny-status" /> Room for the good work.</div>
        <div className="floating-note note-bottom"><span aria-hidden="true">↳</span> Real app. Sample data.</div>
      </div>
    </section>

    <section className="value-strip wrap" aria-label="Product principles">
      <div data-reveal><span>01</span><p>One place for<br /><strong>the everyday work.</strong></p></div>
      <div data-reveal data-delay="1"><span>02</span><p>Helpful AI.<br /><strong>Human decisions.</strong></p></div>
      <div data-reveal data-delay="2"><span>03</span><p>Your community.<br /><strong>Your data.</strong></p></div>
    </section>

    <section className="section wrap" id="inside">
      <div className="section-heading"><div data-reveal><p className="eyebrow coral">A LITTLE LESS SCATTERED</p><h2>The work is important.<br /><em>The software should help.</em></h2></div><p data-reveal data-delay="1">Start with the people you support. Keep the practical details in reach. Give your team a workspace that makes sense.</p></div>
      <div className="feature-grid">
        <article className="feature-card" data-reveal>
          <div className="feature-art people-art" aria-hidden="true"><span className="person person-a">AR</span><span className="person person-b">JM</span><span className="person person-c">SC</span><i className="connection-line" /><b className="art-check">✓</b></div>
          <span className="feature-number">01 / PEOPLE</span><h3>Every connection,<br />cared for.</h3><p>Bring in your contact spreadsheet, review duplicates, and keep conversations connected to the right person.</p><a className="feature-link" href="#tour">A home for your contacts <span aria-hidden="true">↗</span></a>
        </article>
        <article className="feature-card" data-reveal data-delay="1">
          <div className="feature-art schedule-art" aria-hidden="true"><div className="mini-calendar"><span>THIS WEEK</span><div><i>M</i><i>T</i><i>W</i><i>T</i><i>F</i></div><div><b>12</b><b>13</b><b className="calendar-day">14</b><b>15</b><b>16</b></div></div><span className="calendar-label"><i /> Community pantry</span></div>
          <span className="feature-number">02 / COORDINATION</span><h3>Make room for<br />the good work.</h3><p>Organize volunteer applications and schedules, with the everyday context your coordinators need.</p><a className="feature-link" href="#how-it-works">See how to get started <span aria-hidden="true">↗</span></a>
        </article>
        <article className="feature-card" data-reveal data-delay="2">
          <div className="feature-art writing-art" aria-hidden="true"><div className="mini-draft"><span>Thank you for being here.</span><i /><i /><i /></div><span className="draft-label"><b>✳</b> A draft. Your decision.</span></div>
          <span className="feature-number">03 / ASSISTANCE</span><h3>A starting point<br />for the words.</h3><p>Prepare a reply, translate a message, or make a notice clearer. Review every draft before using it.</p><Link className="feature-link" href="/guide#ai">Meet the writing assistant <span aria-hidden="true">↗</span></Link>
        </article>
      </div>
    </section>

    <div className="marquee" aria-hidden="true"><div className="marquee-track">{[0, 1, 2, 3].map((item) => <span key={item}>Less juggling <b>✳</b> More connecting <b>✳</b> A little more hope <b>✳</b></span>)}</div></div>

    <section className="tour-section wrap" id="tour" aria-label="Explore the real application" data-reveal><ProductTour /></section>

    <section className="how-section wrap" id="how-it-works">
      <div className="how-heading" data-reveal><p className="eyebrow coral">FROM DOWNLOAD TO FIRST LOOK</p><h2>Three small steps.<br /><em>A fresh start.</em></h2><p>You do not need to be the technical person.<br />You just need a little curiosity.</p><a className="quiet-link" href="#download">Let’s get you started <span aria-hidden="true">↓</span></a></div>
      <div className="steps"><article data-reveal><span className="step-number">01</span><div><h3>Pick your computer.</h3><p>Choose the installer for your operating system. The download starts right here.</p></div></article><article data-reveal data-delay="1"><span className="step-number">02</span><div><h3>Install. Open. You’re in.</h3><p>The app prepares a private sample workspace. No account, server address, or developer tools needed.</p></div></article><article data-reveal data-delay="2"><span className="step-number">03</span><div><h3>Make yourself at home.</h3><p>Explore fictional contacts, try edits, and find your way around. Your sample changes stay when you come back.</p></div></article></div>
    </section>

    <section className="human-section">
      <div className="wrap human-grid"><div className="human-visual" data-reveal><div className="human-ring ring-a" /><div className="human-ring ring-b" /><div className="human-ring ring-c" /><Image src="/hope-mark.png" alt="" width={230} height={230} sizes="230px" /><span className="human-label">PEOPLE AT THE CENTRE.</span></div>
        <div data-reveal data-delay="1"><p className="eyebrow coral">HELPFUL BY DESIGN</p><h2>The assistant helps.<br /><em>You decide.</em></h2><p className="body-copy">Technology should give your team a useful starting point, without taking the decisions out of your hands.</p><ul className="check-list"><li>Drafts stay drafts until you review them.</li><li>AI results and basic templates are clearly labelled.</li><li>The sample cannot send messages or invite real people.</li><li>No automatic grant or eligibility decisions.</li></ul><Link className="quiet-link" href="/release-notes">What is ready today <span aria-hidden="true">↗</span></Link></div>
      </div>
    </section>

    <section className="download-section" id="download">
      <div className="download-glow" aria-hidden="true" /><div className="download-orbit" aria-hidden="true" />
      <div className="wrap"><div className="download-heading" data-reveal><p className="eyebrow"><span className="live-dot" /> DESKTOP PREVIEW · VERSION {release.version}</p><h2>A workspace worth<br /><em>opening.</em></h2><p>Download. Install. Explore.<br />Your first look is already set up.</p></div>
        <Downloads />
        <p className="download-note" data-reveal>Preview installers are not code-signed. Your computer may show a publisher warning. Use fictional data in the sample. <Link href="/guide#verify">Download safety & installation help ↗</Link></p>
      </div>
    </section>

    <section className="next-step wrap"><div data-reveal><p className="eyebrow coral">WHEN YOUR TEAM IS READY</p><h2>From a first look<br /><em>to your own workspace.</em></h2></div><div data-reveal data-delay="1"><p>The sample is a working workspace on one computer. To share real records across your charity, you’ll need a separately hosted workspace with secure sign-in, email, backups, and a responsible operator.</p><p className="small-copy">Downloading the app does not automatically create a managed charity account.</p><Link className="button outline" href="/guide#team">Explore team setup <span aria-hidden="true">↗</span></Link></div></section>
    <section className="faq wrap" id="questions"><div data-reveal><p className="eyebrow coral">GOOD QUESTIONS</p><h2>A few things<br /><em>worth knowing.</em></h2><span className="faq-flower" aria-hidden="true">✳</span></div><div data-reveal data-delay="1"><Questions /></div></section>
    <div className="closing-line wrap" data-reveal><span>Here’s to the work that matters.</span><a href="#download" aria-label="Go to downloads">↗</a></div>
  </main>;
}
