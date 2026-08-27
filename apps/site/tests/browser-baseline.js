JSON.stringify({
  title: document.title,
  bodyLength: document.body.innerText.length,
  errorOverlay: Boolean(document.querySelector("[data-nextjs-dialog], .vite-error-overlay")),
  externalRepositoryLinks: [...document.links].filter((link) => /github/i.test(link.href)).length,
  horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
  motion: document.documentElement.dataset.motion,
  headings: document.querySelectorAll("h1").length,
  imageFailures: [...document.images].filter((image) => image.complete && image.naturalWidth === 0).map((image) => image.src),
});
