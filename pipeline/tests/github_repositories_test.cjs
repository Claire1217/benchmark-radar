const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const listeners = () => ({ events: {}, addEventListener(type, callback) { this.events[type] = callback; } });
const trigger = {...listeners(), focus() { document.activeElement = this; }};
const link = {};
const menu = {...listeners(), open: false, querySelector() { return trigger; }, contains(node) { return [this, trigger, link].includes(node); }};
const document = {...listeners(), activeElement: null, querySelectorAll() { return [menu]; }};
let timer;
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../web/github-repositories.js'), 'utf8'), {
  document, setTimeout(fn) { timer = fn; return 1; }, clearTimeout() { timer = null; }
});
const flush = () => { const fn = timer; timer = null; if (fn) fn(); };
const click = () => trigger.events.click({preventDefault() {}});
menu.events.pointerenter({pointerType:'touch'}); flush(); assert.equal(menu.open, false);
click(); assert.equal(menu.open, true); click(); assert.equal(menu.open, false);
menu.events.pointerenter({pointerType:'mouse'}); flush(); assert.equal(menu.open, true);
menu.events.pointerleave(); menu.events.pointerenter({pointerType:'mouse'}); flush(); assert.equal(menu.open, true);
menu.events.pointerleave(); flush(); assert.equal(menu.open, false);
click(); menu.events.pointerleave(); flush(); assert.equal(menu.open, true);
document.events.pointerdown({target:{}}); assert.equal(menu.open, false);
click(); document.activeElement = link; menu.events.pointerleave(); flush(); assert.equal(menu.open, true);
menu.events.focusout({relatedTarget:trigger}); assert.equal(menu.open, true);
menu.events.focusout({relatedTarget:null}); assert.equal(menu.open, false);
click(); menu.events.keydown({key:'Escape',stopPropagation(){}}); assert.equal(menu.open, false); assert.equal(document.activeElement, trigger);
console.log('GitHub menu: hover, pointer bridge, touch, toggle, focus and Escape passed');
