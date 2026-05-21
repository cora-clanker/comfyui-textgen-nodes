// Unit tests for the Refine Text state machine.
//
// Run with:
//   node --test tests/test_refine_text_state.mjs
//
// The reducers in web/js/refine_text_state.js are deliberately free of
// browser/ComfyUI references; these tests import them directly and assert
// the five behaviors the lock toggle promises.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  INITIAL_STATE,
  onCreate,
  onReceiveUpstream,
  onUserEdit,
  onUserToggleLock,
} from "../web/js/refine_text_state.js";

test("on create: empty field, lock false", () => {
  const s = onCreate();
  assert.equal(s.editedText, "");
  assert.equal(s.lock, false);
  assert.equal(s.lastSyncedUpstream, undefined);
  assert.equal(s.warned, false);
});

test("INITIAL_STATE is frozen so reducers can't mutate it by accident", () => {
  assert.throws(() => {
    INITIAL_STATE.lock = true;
  }, TypeError);
});

test("receive upstream while unlocked: replace text, sync baseline, lock stays false", () => {
  const s = onReceiveUpstream(onCreate(), "hello world");
  assert.equal(s.editedText, "hello world");
  assert.equal(s.lastSyncedUpstream, "hello world");
  assert.equal(s.lock, false);
  assert.equal(s.warned, false);
});

test("receive upstream while locked WITH drift: warn, lock stays true, text untouched", () => {
  // Sync a baseline first, then lock it, then upstream changes.
  const s0 = onReceiveUpstream(onCreate(), "v1");
  const s1 = onUserToggleLock(s0, true);
  const s2 = onReceiveUpstream(s1, "v2");

  assert.equal(s2.lock, true);
  assert.equal(s2.warned, true);
  // Widget value should not be clobbered by upstream while locked.
  assert.equal(s2.editedText, "v1");
  // Baseline doesn't advance just because we saw new upstream while locked;
  // it should only advance on a real (passthrough) sync.
  assert.equal(s2.lastSyncedUpstream, "v1");
});

test("receive upstream while locked WITHOUT drift: no warning", () => {
  const s0 = onReceiveUpstream(onCreate(), "stable");
  const s1 = onUserToggleLock(s0, true);
  const s2 = onReceiveUpstream(s1, "stable");
  assert.equal(s2.warned, false);
  assert.equal(s2.lock, true);
});

test("receive upstream while locked but no prior sync: no false warning", () => {
  // Edge: user creates the node already locked (e.g. via workflow JSON) and
  // an upstream value arrives. With no baseline, drift is undefined -- don't
  // warn.
  const s = onReceiveUpstream({ ...onCreate(), lock: true }, "anything");
  assert.equal(s.warned, false);
  assert.equal(s.lock, true);
});

test("text edit while unlocked: lock flips to true", () => {
  const s = onUserEdit(onCreate(), "user typed something");
  assert.equal(s.lock, true);
  assert.equal(s.editedText, "user typed something");
});

test("text edit while locked: lock stays true, text updates", () => {
  const s0 = onUserToggleLock(onCreate(), true);
  const s1 = onUserEdit(s0, "edit while locked");
  assert.equal(s1.lock, true);
  assert.equal(s1.editedText, "edit while locked");
});

test("SPECIAL CASE: delete all text while unlocked keeps lock false", () => {
  // First sync some upstream, then clear it -- lock must stay false so the
  // next run resyncs from upstream instead of stranding the node empty.
  const s0 = onReceiveUpstream(onCreate(), "some upstream text");
  assert.equal(s0.lock, false);
  const s1 = onUserEdit(s0, "");
  assert.equal(s1.lock, false);
  assert.equal(s1.editedText, "");
});

test("delete all text while already locked: lock stays locked (special case is unlock-direction only)", () => {
  // The special case only inhibits auto-locking; it does not auto-unlock.
  const s0 = onUserToggleLock(onCreate(), true);
  const s1 = onUserEdit(s0, "");
  assert.equal(s1.lock, true);
  assert.equal(s1.editedText, "");
});

test("untick lock clears the warning state", () => {
  const s0 = onReceiveUpstream(onCreate(), "v1");
  const s1 = onUserToggleLock(s0, true);
  const s2 = onReceiveUpstream(s1, "v2");
  assert.equal(s2.warned, true);

  const s3 = onUserToggleLock(s2, false);
  assert.equal(s3.lock, false);
  assert.equal(s3.warned, false);
});

test("passthrough run after a warning clears the warning and updates baseline", () => {
  const s0 = onReceiveUpstream(onCreate(), "v1");
  const s1 = onUserToggleLock(s0, true);
  const s2 = onReceiveUpstream(s1, "v2"); // warned
  const s3 = onUserToggleLock(s2, false); // user unlocks
  const s4 = onReceiveUpstream(s3, "v2"); // passthrough syncs to the new value

  assert.equal(s4.warned, false);
  assert.equal(s4.editedText, "v2");
  assert.equal(s4.lastSyncedUpstream, "v2");
});

test("reducers do not mutate the input state object", () => {
  const before = onCreate();
  const snapshot = { ...before };
  onReceiveUpstream(before, "x");
  onUserEdit(before, "y");
  onUserToggleLock(before, true);
  assert.deepEqual(before, snapshot);
});
