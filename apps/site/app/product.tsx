"use client";

import Image from "next/image";
import Link from "next/link";
import { useState, useSyncExternalStore } from "react";
import { displaySize, downloadPath, getAsset, platforms, release } from "../lib/releases";
import { TiltSurface } from "./motion";

function detectedPlatform() {
  if (/Android|iPhone|iPad/.test(navigator.userAgent)) return null;
  if (/Windows/.test(navigator.userAgent)) return "windows";
  if (/Macintosh|Mac OS X/.test(navigator.userAgent)) return "mac";
  if (/Linux/.test(navigator.userAgent)) return "linux";
  return null;
}
const subscribe = () => () => {};

export function Downloads() {
  const detected = useSyncExternalStore(subscribe, detectedPlatform, () => null);
  const [started, setStarted] = useState("");
  const debFile = "Project-Hope-" + release.version + "-linux-amd64.deb";
  return <>
    <div className="download-cards">{platforms.map((platform, index) => {
      const asset = getAsset(platform.file);
      return <article key={platform.id} className={"download-card" + (detected === platform.id ? " recommended" : "")} data-reveal data-delay={String(index)}>
        <div className="platform-top"><span className={"platform-symbol platform-" + platform.id} aria-hidden="true">{platform.id === "windows" ? <><i /><i /><i /><i /></> : platform.id === "mac" ? "⌘" : "⌁"}</span><span className="platform-detected">{detected === platform.id ? "YOUR OPERATING SYSTEM" : "DESKTOP APP"}</span></div>
        <h3>{platform.title}</h3><p className="format">{platform.format}</p>
        {asset?.available ? <a className="button light" href={downloadPath(platform.file)} download onClick={() => setStarted(platform.title)}>Download for {platform.title}<span aria-hidden="true">↓</span></a> : <button className="button light" type="button" disabled>Installer being verified</button>}
        <div className="asset-meta"><span>v{release.version}</span><span>{asset?.available ? displaySize(asset.bytes) : "Available after verification"}</span></div>
        <p className="platform-note">{platform.note}</p>
      </article>;
    })}</div>
    <p className="download-status" role="status" aria-live="polite">{started ? "Your " + started + " download should start now. Then follow the installation guide below." : "Choose your computer. The installer downloads directly from this site."}{started && <> <Link href="/guide">Open installation help ↗</Link></>}</p>
    <div className="download-extras">{getAsset(debFile)?.available && <a href={downloadPath(debFile)} download>Linux .deb package <span aria-hidden="true">↓</span></a>}<Link href="/guide#verify">Verify your download <span aria-hidden="true">↗</span></Link><Link href="/release-notes">Release notes <span aria-hidden="true">↗</span></Link></div>
  </>;
}

const screens = [
  { id: "import", label: "Bring your contacts", image: "contacts.png", title: "A careful move, not a leap of faith.", body: "Preview a spreadsheet, check each row, and decide what to create, update, or skip before making changes.", caption: "Actual Project Hope import review · fictional demonstration records" },
  { id: "duplicates", label: "Tidy up duplicates", image: "duplicates.png", title: "Two records. One clearer picture.", body: "Compare possible duplicates side by side, choose which record to keep, and review the merge. The original record remains preserved.", caption: "Actual Project Hope duplicate review · fictional demonstration records" },
];

export function ProductTour() {
  const [active, setActive] = useState(screens[0]);
  return <div className="product-tour">
    <div className="tour-copy"><p className="eyebrow coral">NOT A MOCKUP. YOUR NEXT WORKSPACE.</p><div className="tour-description" key={active.id}><h3>{active.title}</h3><p>{active.body}</p></div>
      <div className="tour-buttons" role="tablist" aria-label="Explore Project Hope">{screens.map((screen, index) => <button type="button" role="tab" key={screen.id} id={"tab-" + screen.id} aria-selected={active.id === screen.id} aria-controls="tour-panel" tabIndex={active.id === screen.id ? 0 : -1} onClick={() => setActive(screen)} onKeyDown={(event) => {
        if (!["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        const next = event.key === "Home" ? 0 : event.key === "End" ? screens.length - 1 : (index + (["ArrowRight", "ArrowDown"].includes(event.key) ? 1 : -1) + screens.length) % screens.length;
        setActive(screens[next]);
        document.getElementById("tab-" + screens[next].id)?.focus();
      }}><span className="tour-index">0{index + 1}</span>{screen.label}<span className="tour-arrow" aria-hidden="true">↗</span></button>)}</div>
      <a className="quiet-link" href="#download">Try it in the desktop app <span aria-hidden="true">↓</span></a>
    </div>
    <div className="tour-panel" role="tabpanel" id="tour-panel" aria-labelledby={"tab-" + active.id} tabIndex={0}><TiltSurface><figure>
      <div className="tour-screen" key={active.image}><Image src={"/images/" + active.image} alt={active.caption} width={1440} height={1100} sizes="(max-width: 900px) 85vw, 55vw" /></div>
      <figcaption><span className="tiny-status" />{active.caption}</figcaption>
    </figure></TiltSurface></div>
  </div>;
}
