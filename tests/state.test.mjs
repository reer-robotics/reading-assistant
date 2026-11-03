import {test} from 'node:test';
import assert from 'node:assert/strict';
import {RequestState, insertAtCodePoint} from '../src/reading_assistant/web/state.js';
test('requests do not overlap; unchanged automatic checks skip', () => {
  const state = new RequestState();
  const request = state.begin();
  assert.equal(state.begin(), null);
  assert.equal(state.finish(request, true), true);
  assert.equal(state.begin(true), null);
  assert.equal(state.stale, false);
});
test('editing during analysis rejects old results even after reverting text', () => {
  const state = new RequestState(); const request = state.begin();
  state.edit(); state.edit();
  assert.equal(state.finish(request, true), false);
  assert.equal(state.stale, true);
  const next = state.begin(true);
  assert.equal(state.finish(next, true), true);
});
test('failure permits manual retry and retains stale state', () => {
  const state = new RequestState(); const request = state.begin();
  assert.equal(state.finish(request, false), false);
  assert.equal(state.begin(), 0);
});
test('citation insertion honors Python code point offsets after emoji', () => {
  assert.equal(insertAtCodePoint('🚀 Test\n\nNext', 6, ' [^note]'), '🚀 Test [^note]\n\nNext');
});
