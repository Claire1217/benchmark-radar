/* Native details remains usable even when this enhancement cannot load. */
document.querySelectorAll('.github-repositories').forEach(menu => {
  const trigger = menu.querySelector('summary');
  let pinned = false;
  let timer;
  const close = () => { clearTimeout(timer); pinned = false; menu.open = false; };
  trigger.addEventListener('click', event => {
    event.preventDefault();
    clearTimeout(timer);
    pinned = !pinned;
    menu.open = pinned;
  });
  menu.addEventListener('pointerenter', event => {
    if (event.pointerType !== 'mouse') return;
    clearTimeout(timer);
    timer = setTimeout(() => { menu.open = true; }, 120);
  });
  menu.addEventListener('pointerleave', () => {
    clearTimeout(timer);
    if (!pinned) timer = setTimeout(() => {
      if (!menu.contains(document.activeElement)) close();
    }, 200);
  });
  menu.addEventListener('focusout', event => {
    if (!menu.contains(event.relatedTarget)) close();
  });
  menu.addEventListener('keydown', event => {
    if (event.key === 'Escape') { close(); trigger.focus(); event.stopPropagation(); }
  });
  document.addEventListener('pointerdown', event => {
    if (!menu.contains(event.target)) close();
  });
});
