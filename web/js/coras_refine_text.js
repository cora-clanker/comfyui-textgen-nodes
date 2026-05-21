import { app } from "../../scripts/app.js";
import {
  onCreate,
  onReceiveUpstream,
  onUserEdit,
  onUserToggleLock,
} from "./refine_text_state.js";

// Frontend behavior for the Refine Text node (CorasRefineText).
//
// All state-transition logic lives in refine_text_state.js (pure, unit-tested).
// This file is the DOM/litegraph glue:
//   * wires user events (edit, toggle lock) and execution results to the
//     reducers;
//   * applies the resulting side effects -- writes the widget value, sets the
//     warning color on the node, logs to the console on warning transitions;
//   * persists the drift baseline into node.properties (which IS serialized
//     into the workflow JSON, so the baseline survives reloads).
//
// litegraph only fires widget.callback on real user interaction, so the
// programmatic writes from onExecuted never trip the auto-lock or the
// "delete-all stays unlocked" special case.

const WARN_COLOR = "#a55a1a";

function applyWarning(node, on) {
  if (!!on === !!node._refineWarned) return;
  if (on) {
    node._refineOrigColor = node.color;
    node.color = WARN_COLOR;
    node._refineWarned = true;
  } else {
    node.color = node._refineOrigColor;
    delete node._refineOrigColor;
    delete node._refineWarned;
  }
  app.graph?.setDirtyCanvas(true, true);
}

// Read current observable state off the widgets + persisted properties.
function readState(node) {
  const edited = node.widgets?.find((w) => w.name === "edited_text");
  const lock = node.widgets?.find((w) => w.name === "lock");
  return {
    lock: !!lock?.value,
    editedText: edited?.value ?? "",
    lastSyncedUpstream: node.properties?.lastSyncedUpstream,
    warned: !!node._refineWarned,
  };
}

// Push computed state back into widgets / properties / visuals.
function writeState(node, prev, next) {
  const edited = node.widgets?.find((w) => w.name === "edited_text");
  const lock = node.widgets?.find((w) => w.name === "lock");

  if (lock && lock.value !== next.lock) lock.value = next.lock;
  if (edited && edited.value !== next.editedText) edited.value = next.editedText;

  node.properties = node.properties ?? {};
  if (node.properties.lastSyncedUpstream !== next.lastSyncedUpstream) {
    node.properties.lastSyncedUpstream = next.lastSyncedUpstream;
  }

  if (!prev.warned && next.warned) {
    console.warn(
      `[Refine Text] node #${node.id}: upstream produced new text while lock is on. ` +
        `Untick lock to resync.`,
    );
  }
  applyWarning(node, next.warned);
}

app.registerExtension({
  name: "comfyui-coras-textgen-nodes.refine-text",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "CorasRefineText") return;

    const origCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      origCreated?.apply(this, arguments);
      this.serialize_widgets = true;

      const node = this;
      const edited = node.widgets?.find((w) => w.name === "edited_text");
      const lock = node.widgets?.find((w) => w.name === "lock");
      if (!edited || !lock) return;

      // Seed defaults via onCreate(). We don't clobber values that the
      // workflow JSON loader has already populated (loader runs after
      // onNodeCreated), so this only matters for freshly added nodes.
      const seeded = onCreate();
      if (edited.value === undefined || edited.value === null) {
        edited.value = seeded.editedText;
      }
      if (lock.value === undefined || lock.value === null) {
        lock.value = seeded.lock;
      }

      const origEditedCb = edited.callback;
      edited.callback = function (value) {
        const r = origEditedCb?.call(this, value);
        const prev = readState(node);
        // value param reflects what the widget now holds (post-user-edit).
        const next = onUserEdit(prev, value ?? "");
        writeState(node, prev, next);
        return r;
      };

      const origLockCb = lock.callback;
      lock.callback = function (value) {
        const r = origLockCb?.call(this, value);
        const prev = readState(node);
        const next = onUserToggleLock(prev, !!value);
        writeState(node, prev, next);
        return r;
      };
    };

    const origExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      origExecuted?.apply(this, arguments);
      const edited = this.widgets?.find((w) => w.name === "edited_text");
      const lock = this.widgets?.find((w) => w.name === "lock");
      if (!edited || !lock) return;

      const raw = message?.upstream_text;
      const upstream = Array.isArray(raw) ? raw[0] ?? "" : raw ?? "";

      const prev = readState(this);
      const next = onReceiveUpstream(prev, upstream);
      writeState(this, prev, next);
    };

    const origSerialize = nodeType.prototype.onSerialize;
    nodeType.prototype.onSerialize = function (o) {
      origSerialize?.apply(this, arguments);
      // Don't persist the transient warning color into the workflow JSON.
      if (this._refineWarned) {
        if (this._refineOrigColor === undefined) {
          delete o.color;
        } else {
          o.color = this._refineOrigColor;
        }
      }
    };
  },
});
