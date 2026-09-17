/* Render supported inline title math without interpreting arbitrary HTML/TeX. */
function benchmarkNameHtml(value) {
  const escaped = String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  return escaped
    .replace(/\$\\tau\^\\tau\$/g, 'τ<sup>τ</sup>')
    .replace(/\$\^\{?(\d+)\}?\$/g, '<sup>$1</sup>');
}
