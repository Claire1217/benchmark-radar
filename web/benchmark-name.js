/* Render supported title TeX without interpreting arbitrary HTML. */
function benchmarkNameHtml(value) {
  const combining={
    '=':'\u0304', "'":'\u0301', '`':'\u0300', '^':'\u0302', '"':'\u0308',
    '~':'\u0303', '.':'\u0307', 'u':'\u0306', 'v':'\u030c', 'H':'\u030b',
    'c':'\u0327', 'k':'\u0328', 'r':'\u030a', 'b':'\u0331', 'd':'\u0323', 't':'\u0361'
  };
  const accent=(character,command)=>(character+combining[command]).normalize('NFC');
  const normalized=String(value??'')
    // Symbol accent commands may use either `\\={a}` or the shorter `\\=a`.
    .replace(/\\([="'`^~.])\s*(?:\{([^{}])\}|([A-Za-z]))/g,(_,command,braced,bare)=>accent(braced??bare,command))
    // Letter accent commands require braces so `\\tau` cannot be read as `\\t{a}`.
    .replace(/\\([uvHckbdtr])\s*\{([^{}])\}/g,(_,command,character)=>accent(character,command));
  const escaped = normalized.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  return escaped
    .replace(/\$\\tau\^\\tau\$/g, 'τ<sup>τ</sup>')
    .replace(/\$\^\{?(\d+)\}?\$/g, '<sup>$1</sup>');
}
