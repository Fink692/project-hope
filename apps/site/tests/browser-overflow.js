JSON.stringify({
  innerWidth,
  documentWidth: document.documentElement.scrollWidth,
  bodyWidth: document.body.scrollWidth,
  elements: [...document.querySelectorAll("body *")].map((element) => ({ tag: element.tagName, className: element.className, left: element.getBoundingClientRect().left, right: element.getBoundingClientRect().right, width: element.getBoundingClientRect().width })).filter((element) => element.right > innerWidth + 1 || element.left < -1).slice(0, 35)
});
