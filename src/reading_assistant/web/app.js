import {RequestState, insertAtCodePoint} from './state.js';
const $ = id => document.getElementById(id);
const state = new RequestState();
const palette = ['teal', 'violet', 'amber', 'blue', 'rose', 'olive'];
let config, result = null, resultDraft = '', timer = null;
const dismissed = new Set(), notes = new Map();
const labels = {suggested_reading: 'Suggested reading', possible_citation: 'Possible citation', possible_conflict: 'Possible conflict'};
function element(tag, className, text) { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; }
function button(text, handler, className) { const node = element('button', className, text); node.addEventListener('click', handler); return node; }
function status(text) { $('status').textContent = text; }
function updateCount() { $('word-count').textContent = `${$('editor').value.trim().split(/\s+/).filter(Boolean).length} words`; }
function setEdit(editing) { $('editor').hidden = !editing; $('linked').hidden = editing; $('edit-tab').setAttribute('aria-pressed', String(editing)); $('linked-tab').setAttribute('aria-pressed', String(!editing)); if (editing) $('editor').focus(); }
function draftChanged() {
  state.edit(); updateCount(); renderDraft();
  $('stale').hidden = !result;
  document.querySelectorAll('[data-insert]').forEach(node => node.disabled = true);
  status('Draft changed. Recommendations will refresh on request or at the next enabled interval.');
}
function renderDraft() {
  const linked = $('linked'); linked.replaceChildren();
  const fresh = result && !state.stale;
  const passages = fresh ? result.paragraphs : $('editor').value.split(/\n\s*\n/).map(t => t.trim()).filter(Boolean).map((text, index) => ({text, id: `current-${index}`, label: `P${index + 1}`, color: palette[index % palette.length]}));
  if (!passages.length) linked.append(element('p', 'hint', 'Switch to Edit and start a paragraph.'));
  for (const p of passages) {
    const matches = fresh ? result.recommendations.filter(c => c.passage_id === p.id && !dismissed.has(c.id)) : [];
    const block = element('article', `passage ${matches.length ? p.color : 'unmatched'}`);
    block.id = p.id;
    const head = element('div', 'passage-head'); head.append(element('span', 'badge', p.label));
    if (matches.length) head.append(button(`${matches.length} reading suggestions ↗`, () => { $('passage-filter').value = p.id; renderCards(); $('reading-title').scrollIntoView({block: 'start'}); }));
    else head.append(element('span', 'metadata', fresh ? 'No matching sources' : 'Awaiting recommendations'));
    block.append(head, element('p', '', p.text)); linked.append(block);
  }
}
function focusPassage(id) {
  setEdit(false);
  document.querySelectorAll('.passage.active').forEach(n => n.classList.remove('active'));
  const node = document.getElementById(id);
  if (!node || state.stale) { status('Refresh recommendations to reconnect this card to the current draft.'); return; }
  node.classList.add('active'); node.scrollIntoView({block: 'center'});
}
async function openSource(card) {
  try {
    const response = await fetch(`/api/sources/${encodeURIComponent(card.source.id)}`);
    if (!response.ok) throw new Error('Source unavailable for this session.');
    const source = await response.json();
    $('source-title').textContent = source.title;
    const body = $('source-body'); body.replaceChildren();
    body.append(element('p', 'metadata', `${source.origin === 'internal' ? 'Internal' : 'Curated external'} · ${source.maturity.replaceAll('_', ' ')} · ${source.version}`));
    if (source.synthetic) body.append(element('p', 'warning', 'Synthetic example — not company evidence or an adopted policy.'));
    for (const passage of source.passages) body.append(element('h3', '', passage.locator), element('p', '', passage.text));
    if (source.url) { const link = element('a', '', 'Visit original source ↗'); link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; body.append(link); }
    $('source-dialog').showModal();
  } catch (error) { status(error.message); }
}
async function copyCitation(card) {
  try { await navigator.clipboard.writeText(`${card.citation.marker}\n${card.citation.markdown}`); status('Citation copied as a Markdown source note.'); }
  catch { status('Clipboard unavailable. Expand Citation format to select and copy the source note.'); }
}
function insertCitation(card) {
  if (state.stale || $('editor').value !== resultDraft) { status('Refresh recommendations before inserting.'); return; }
  const passage = result.paragraphs.find(p => p.id === card.passage_id);
  if (passage.text.includes(card.citation.marker)) { status('This passage already contains that citation.'); return; }
  $('editor').value = insertAtCodePoint($('editor').value, passage.end, ` ${card.citation.marker}`);
  notes.set(card.citation.key, card.citation.markdown);
  renderNotes(); draftChanged(); setEdit(true);
  status(`Inserted a source note at the end of ${card.label}. Review its relevance; refresh for more insertions.`);
}
function renderNotes() {
  $('notes').replaceChildren();
  for (const note of notes.values()) $('notes').append(element('p', '', note));
  $('note-count').textContent = `(${notes.size})`;
}
function renderCards() {
  const container = $('cards'); container.replaceChildren();
  if (!result) return;
  const visible = result.recommendations.filter(c => !dismissed.has(c.id) && ($('passage-filter').value === 'all' || c.passage_id === $('passage-filter').value) && ($('kind-filter').value === 'all' || c.kind === $('kind-filter').value));
  $('result-count').textContent = String(visible.length);
  $('restore').hidden = !dismissed.size;
  if (!visible.length) {
    container.append(element('div', 'empty', 'No recommendations match this view. Try another passage or filter, or add relevant sources to your catalog.'));
    return;
  }
  for (const card of visible) {
    const item = element('article', `card ${card.color}`);
    const head = element('div', 'card-head'); head.append(button(`${card.label} ↖`, () => focusPassage(card.passage_id)), element('span', '', labels[card.kind]), element('span', '', `· #${card.rank}`));
    item.append(head, element('h3', '', card.source.title), element('div', 'metadata', `${card.source.origin === 'internal' ? 'Internal' : 'Curated external'} · ${card.source.maturity.replaceAll('_', ' ')}${card.source.synthetic ? ' · SYNTHETIC' : ''}`), element('p', 'reason', card.reason), element('blockquote', 'evidence', card.evidence.text), element('div', 'locator', card.evidence.locator), element('p', 'caveat', card.caveat));
    const details = element('details'); details.append(element('summary', '', 'Citation format · source-note v1'), element('p', '', `${card.citation.marker}\n${card.citation.markdown}`));
    if (card.citation.missing_fields.length) details.append(element('p', '', `Not supplied: ${card.citation.missing_fields.join(', ')}.`));
    item.append(details);
    const actions = element('div', 'actions');
    const insert = button('Insert citation', () => insertCitation(card)); insert.dataset.insert = card.id; insert.disabled = state.stale;
    actions.append(button('Open source', () => openSource(card)), button('Copy citation', () => copyCitation(card)), insert, button('Dismiss', () => { dismissed.add(card.id); renderCards(); renderDraft(); }, 'dismiss'));
    item.append(actions); container.append(item);
  }
}
async function recommend(automatic = false) {
  if (!config || (automatic && document.hidden)) return;
  const text = $('editor').value;
  if (!text.trim()) { if (!automatic) status('Write a paragraph first.'); return; }
  const revision = state.begin(automatic);
  if (revision === null) return;
  $('recommend').disabled = true; status('Finding passages in your library…');
  try {
    const response = await fetch('/api/recommend', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Reading-Token': config.token}, body: JSON.stringify({draft: text})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Recommendation request failed.');
    if (!state.finish(revision, true)) { status('The draft changed during analysis. Results were discarded; refresh when ready.'); return; }
    result = data; resultDraft = text; dismissed.clear();
    const filter = $('passage-filter'); filter.replaceChildren(new Option('All passages', 'all'));
    for (const p of result.paragraphs) filter.append(new Option(`${p.label} · ${p.text.slice(0, 24)}…`, p.id));
    $('stale').hidden = true; renderDraft(); renderCards();
    $('stats').textContent = `${result.recommendations.length} suggestions · ${result.paragraphs.length} passages`;
    status(`${data.mode === 'lexical' ? 'Keyword matches ready; AI support/conflict review was not run.' : 'Local AI suggestions ready for your review.'} Updated ${new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}.`);
  } catch (error) {
    state.finish(revision, false); status(`${error.message} Automatic updates paused.`);
    $('automatic').checked = false; configureTimer();
  } finally { $('recommend').disabled = false; }
}
function configureTimer() {
  if (timer) clearInterval(timer);
  timer = null;
  if ($('automatic').checked) timer = setInterval(() => recommend(true), Number($('interval').value) * 1000);
}
function download() {
  const activeNotes = [...notes].filter(([key]) => $('editor').value.includes(`[^${key}]`)).map(([, note]) => note);
  const content = $('editor').value + (activeNotes.length ? '\n\n' + activeNotes.join('\n\n') : '') + '\n';
  const url = URL.createObjectURL(new Blob([content], {type: 'text/markdown;charset=utf-8'}));
  const link = element('a'); link.href = url; link.download = 'reading-draft.md'; link.click(); URL.revokeObjectURL(url);
  status('Markdown download prepared with the inserted source notes.');
}
$('recommend').addEventListener('click', () => recommend(false));
$('automatic').addEventListener('change', () => { configureTimer(); status($('automatic').checked ? 'Automatic checks enabled. Only changed drafts are analyzed; hidden tabs pause requests.' : 'Automatic checks off.'); });
$('interval').addEventListener('change', configureTimer);
$('editor').addEventListener('input', draftChanged);
$('edit-tab').addEventListener('click', () => setEdit(true));
$('linked-tab').addEventListener('click', () => setEdit(false));
$('passage-filter').addEventListener('change', renderCards);
$('kind-filter').addEventListener('change', renderCards);
$('restore').addEventListener('click', () => { dismissed.clear(); renderCards(); renderDraft(); });
$('download').addEventListener('click', download);
$('close-source').addEventListener('click', () => $('source-dialog').close());
$('load-demo').addEventListener('click', () => {
  if ($('editor').value && !window.confirm('Replace the current in-memory draft with the synthetic example? Download first to keep it.')) return;
  $('editor').value = config.demo_draft; notes.clear(); renderNotes(); draftChanged();
});
window.addEventListener('pagehide', () => { if (timer) clearInterval(timer); });
try {
  const response = await fetch('/api/config'); if (!response.ok) throw new Error('Could not load the local configuration.');
  config = await response.json(); $('editor').value = config.demo_draft;
  $('mode').textContent = config.model ? `Local model: ${config.model}` : 'Keyword mode · no AI model';
  $('library-count').textContent = `${config.sources} permitted sources · demo library`;
  updateCount(); renderDraft(); status('Synthetic example loaded. Choose Recommend now to connect the passages.');
} catch (error) { status(error.message); $('recommend').disabled = true; }
