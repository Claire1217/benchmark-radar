/* Native scrolling, sized to the visible space below the Library hero.
   Do not intercept wheel/touch events or rebuild navigation while scrolling. */
function librarySidebarHeight(viewportHeight, layoutTop, stickyTop) {
  return Math.max(0, viewportHeight - Math.max(stickyTop, layoutTop) - 16);
}

(() => {
  const sidebar = document.querySelector(".library-domains");
  const layout = document.querySelector(".library-layout");
  const view = document.getElementById("library-view");
  if (!sidebar || !layout || !view) return;
  let frame = 0;
  function update() {
    frame = 0;
    if (view.hidden) return;
    if (window.matchMedia("(max-width:760px)").matches) {
      sidebar.style.removeProperty("--library-sidebar-height");
      return;
    }
    const viewportHeight = window.visualViewport?.height || window.innerHeight;
    const stickyTop = parseFloat(getComputedStyle(sidebar).top) || 88;
    const height = librarySidebarHeight(viewportHeight, layout.getBoundingClientRect().top, stickyTop);
    sidebar.style.setProperty("--library-sidebar-height", height + "px");
  }
  function schedule() {
    if (!frame) frame = requestAnimationFrame(update);
  }
  window.addEventListener("scroll", schedule, {passive: true});
  window.addEventListener("resize", schedule, {passive: true});
  window.visualViewport?.addEventListener("resize", schedule, {passive: true});
  new MutationObserver(schedule).observe(view, {attributes: true, attributeFilter: ["hidden"]});
  const resize = new ResizeObserver(schedule);
  resize.observe(layout);
  const hero = view.querySelector(".hero");
  if (hero) resize.observe(hero);
  schedule();
})();
