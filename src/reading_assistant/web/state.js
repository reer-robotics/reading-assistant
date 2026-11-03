// Shared pure state helpers; no DOM or network dependency.
export class RequestState {
  constructor() { this.revision = 0; this.busy = false; this.completed = -1; this.accepted = -1; }
  edit() { this.revision += 1; }
  begin(automatic = false) {
    if (this.busy || (automatic && this.completed === this.revision)) return null;
    this.busy = true;
    return this.revision;
  }
  finish(revision, success) {
    this.busy = false;
    if (!success || revision !== this.revision) return false;
    this.completed = revision; this.accepted = revision;
    return true;
  }
  get stale() { return this.accepted !== this.revision; }
}
export function insertAtCodePoint(text, position, addition) {
  const characters = Array.from(text);
  return characters.slice(0, position).join('') + addition + characters.slice(position).join('');
}
