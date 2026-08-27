"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const preferenceEvent = "hope-motion-change";
let sessionPreference: boolean | undefined;
function subscribe(listener: () => void) {
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  media.addEventListener("change", listener);
  window.addEventListener(preferenceEvent, listener);
  window.addEventListener("storage", listener);
  return () => {
    media.removeEventListener("change", listener);
    window.removeEventListener(preferenceEvent, listener);
    window.removeEventListener("storage", listener);
  };
}
function motionPaused() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return true;
  if (sessionPreference !== undefined) return sessionPreference;
  try { return localStorage.getItem("hope-motion") === "paused"; } catch { return false; }
}

export function MotionController() {
  const paused = useSyncExternalStore(subscribe, motionPaused, () => false);
  const pathname = usePathname();
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.motion = paused ? "paused" : "running";
    const reveals = [...document.querySelectorAll<HTMLElement>("[data-reveal]")];
    if (paused) {
      reveals.forEach((item) => { item.dataset.visible = "true"; });
      root.style.setProperty("--scroll", "0");
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          (entry.target as HTMLElement).dataset.visible = "true";
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -28px 0px" });
    reveals.forEach((item) => observer.observe(item));
    root.dataset.motionReady = "true";
    let frame = 0;
    const scenery = [...document.querySelectorAll<HTMLElement>("[data-parallax]")];
    const update = () => {
      frame = 0;
      const height = root.scrollHeight - window.innerHeight;
      root.style.setProperty("--scroll", String(height > 0 ? window.scrollY / height : 0));
      scenery.forEach((item) => {
        const rect = item.getBoundingClientRect();
        if (rect.bottom > -100 && rect.top < innerHeight + 100) {
          const progress = (innerHeight / 2 - rect.top - rect.height / 2) / innerHeight;
          item.style.setProperty("--parallax", (Math.max(-1, Math.min(1, progress)) * 36).toFixed(1) + "px");
        }
      });
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      delete root.dataset.motionReady;
      scenery.forEach((item) => item.style.removeProperty("--parallax"));
    };
  }, [paused, pathname]);

  return <button className="motion-toggle" type="button" aria-pressed={paused} onClick={() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    sessionPreference = !paused;
    try { localStorage.setItem("hope-motion", paused ? "running" : "paused"); } catch { /* A blocked preference store must not break navigation. */ }
    window.dispatchEvent(new Event(preferenceEvent));
  }} title="Your system’s reduced-motion preference is always respected">
    <span className="motion-bars" aria-hidden="true"><i /><i /><i /></span>
    {paused ? "Motion paused" : "Pause motion"}
  </button>;
}

export function Brand({ footer = false }: { footer?: boolean }) {
  return <Link className={"brand" + (footer ? " footer-brand" : "")} href="/" aria-label="Project Hope home">
    <Image src="/hope-mark.png" alt="" width={44} height={44} />
    <span>Project Hope<span className="brand-dot">.</span></span>
  </Link>;
}

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  return <>
    <a className="skip" href="#main">Skip to content</a>
    <div className="scroll-progress" aria-hidden="true" />
    <header className="header">
      <div className="header-inner wrap">
        <Brand />
        <nav className={open ? "main-nav is-open" : "main-nav"} id="main-nav" aria-label="Main navigation" onClick={() => setOpen(false)}>
          <Link href="/#inside">The workspace</Link><Link href="/#how-it-works">How it works</Link><Link href="/guide">A little help</Link>
        </nav>
        <div className="header-actions">
          <Link className="button small" href="/#download">Get Project Hope <span aria-hidden="true">↗</span></Link>
          <button className="menu-toggle" type="button" aria-label={open ? "Close navigation" : "Open navigation"} aria-expanded={open} aria-controls="main-nav" onClick={() => setOpen(!open)}><span /><span /></button>
        </div>
      </div>
    </header>
  </>;
}

export function SiteFooter() {
  return <footer className="footer wrap">
    <div><Brand footer /><p>A little more room for the work that matters.</p></div>
    <nav aria-label="Footer navigation"><Link href="/guide">Getting started</Link><Link href="/release-notes">Release notes</Link><Link href="/privacy">Privacy</Link></nav>
    <p className="footer-fine">Made with care. Built for people.</p>
  </footer>;
}

export function TiltSurface({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={"tilt-surface " + className} onPointerMove={(event) => {
    if (motionPaused() || event.pointerType !== "mouse") return;
    const rect = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--tilt-x", ((event.clientY - rect.top) / rect.height * -5 + 2.5).toFixed(2) + "deg");
    event.currentTarget.style.setProperty("--tilt-y", ((event.clientX - rect.left) / rect.width * 6 - 3).toFixed(2) + "deg");
  }} onPointerLeave={(event) => {
    event.currentTarget.style.setProperty("--tilt-x", "0deg");
    event.currentTarget.style.setProperty("--tilt-y", "0deg");
  }}>{children}</div>;
}

export function Questions() {
  const [active, setActive] = useState<number | null>(0);
  const questions = [
    ["Do I need an account or a server to try it?", <>No. Install the app and a private sample workspace opens automatically. It includes fictional contacts, volunteers, and schedules. Your sample edits are saved on this computer.</>],
    ["Is the download really free?", <>There is no charge to download and explore this preview, and no card is requested. Running a shared charity workspace can involve hosting and service costs. Production licensing terms have not yet been finalized.</>],
    ["Does the AI work immediately?", <>The core workspace works immediately. Model-generated drafts need compatible local Ollama models. Without them, the app offers clearly labelled, limited safety templates—not a pretend AI result. <Link href="/guide#ai">See the AI guide.</Link></>],
    ["Can my whole charity use it together?", <>Yes, with a separately prepared hosted workspace. The app can connect to that workspace using its website address. Downloading the sample does not create a hosted charity account. <Link href="/guide#team">Read about team setup.</Link></>],
    ["Why might my computer show a warning?", <>These preview installers are not code-signed or notarized. Your operating system may warn that the publisher is unverified. Check the download’s SHA-256 checksum and follow your organization’s device policy. <Link href="/guide#verify">How to check your download.</Link></>],
    ["What is available today?", <>A desktop preview for exploring contacts, volunteers, schedules, and reviewable writing assistance. Phone integrations need separate services; mobile-store releases are not available. <Link href="/release-notes">See what is included and what is not.</Link></>],
  ];
  return <div className="faq-list">{questions.map(([title, answer], index) => <article className={active === index ? "faq-item is-open" : "faq-item"} key={index}>
    <h3><button type="button" id={"question-" + index} aria-expanded={active === index} aria-controls={"answer-" + index} onClick={() => setActive(active === index ? null : index)}>{title}<span aria-hidden="true">+</span></button></h3>
    <div className="faq-answer" id={"answer-" + index} role="region" aria-labelledby={"question-" + index} inert={active !== index}><div><p>{answer}</p></div></div>
  </article>)}</div>;
}
