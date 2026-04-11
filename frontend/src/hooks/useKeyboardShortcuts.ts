import { useEffect, useRef } from 'react';

export interface Shortcut {
  /** The KeyboardEvent.key value to match (e.g. '1', 'Tab', 'Escape', 'Enter', '?'). */
  key: string;
  /** Short visual label for cheat-sheet rows (e.g. '1-8', 'Esc', 'Shift+Tab'). */
  label: string;
  /** Human description — shown in the cheat sheet. */
  description: string;
  handler: () => void;
  /** If specified, must exactly match e.shiftKey. Default: undefined (don't check). */
  shift?: boolean;
  /** If specified, must exactly match (e.ctrlKey || e.metaKey). Default: undefined (don't check). */
  ctrl?: boolean;
  /** Allow the shortcut to fire even when focus is inside an input/textarea/select. */
  allowInInput?: boolean;
  /** Skip the shortcut without removing it from the cheat sheet. */
  enabled?: boolean;
}

const INPUT_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT']);

/**
 * Bind keyboard shortcuts. Registers the listener exactly once and reads the latest
 * shortcut array via ref, so rapidly-changing handlers don't churn the event listener.
 *
 * Rules:
 *  - By default shortcuts DO NOT fire while focus is inside an input/textarea/select
 *    or a contentEditable element. Set `allowInInput: true` to override (useful for
 *    barcode scanners that keep an input focused, and for Esc/`?`).
 *  - `shift` and `ctrl` modifiers are checked only when explicitly set — leave
 *    undefined to ignore that modifier.
 */
export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  const ref = useRef(shortcuts);
  ref.current = shortcuts;

  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      const inInput =
        (tag && INPUT_TAGS.has(tag)) || target?.isContentEditable === true;

      for (const s of ref.current) {
        if (s.enabled === false) continue;
        if (inInput && !s.allowInInput) continue;

        // Match key — exact for special keys, case-insensitive for letters
        const keyMatches =
          e.key === s.key || e.key.toLowerCase() === s.key.toLowerCase();
        if (!keyMatches) continue;

        if (s.shift !== undefined && e.shiftKey !== s.shift) continue;
        if (s.ctrl !== undefined) {
          const ctrlHeld = e.ctrlKey || e.metaKey;
          if (ctrlHeld !== s.ctrl) continue;
        }

        e.preventDefault();
        s.handler();
        return;
      }
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);
}
