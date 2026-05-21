// Pure state machine for the Refine Text node.
//
// Kept free of any browser/ComfyUI/litegraph references so the rules can be
// unit-tested under plain Node (`node --test tests/`). The DOM glue lives in
// coras_refine_text.js; it wires real events to these reducers and applies
// the resulting side effects (widget value, node color, console.warn).
//
// State shape:
//   {
//     lock: boolean,
//     editedText: string,
//     lastSyncedUpstream: string | undefined,  // baseline for drift detection
//     warned: boolean,                          // is the stale-lock warning active
//   }
//
// Behaviors enforced (see tests/test_refine_text_state.mjs):
//   1. onCreate                                   -> editedText="", lock=false
//   2. onReceiveUpstream while lock=false         -> replace text, sync baseline, clear warning
//   3. onReceiveUpstream while lock=true & drift  -> warned=true, lock stays true, text untouched
//   4. onUserEdit                                 -> lock=true (auto-engage)
//   5. onUserEdit to "" while lock=false          -> lock STAYS false (special case)
//   6. onUserToggleLock(false)                    -> warning cleared

export const INITIAL_STATE = Object.freeze({
  lock: false,
  editedText: "",
  lastSyncedUpstream: undefined,
  warned: false,
});

export function onCreate() {
  return { ...INITIAL_STATE };
}

export function onReceiveUpstream(state, upstream) {
  const upstreamStr = upstream ?? "";
  if (!state.lock) {
    return {
      ...state,
      editedText: upstreamStr,
      lastSyncedUpstream: upstreamStr,
      warned: false,
    };
  }
  // Locked: compare against baseline. Only warn once a baseline exists --
  // a node that was created already-locked has no prior sync to drift from.
  const drifted =
    state.lastSyncedUpstream !== undefined &&
    upstreamStr !== state.lastSyncedUpstream;
  return { ...state, warned: drifted };
}

export function onUserEdit(state, newText) {
  // Special case: clearing the field while unlocked keeps lock=false so the
  // next run resyncs from upstream instead of stranding the node on "".
  if (newText === "" && !state.lock) {
    return { ...state, editedText: "" };
  }
  return { ...state, editedText: newText, lock: true };
}

export function onUserToggleLock(state, lockValue) {
  if (!lockValue) {
    return { ...state, lock: false, warned: false };
  }
  return { ...state, lock: true };
}
