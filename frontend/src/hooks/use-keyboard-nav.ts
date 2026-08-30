'use client';

import { useEffect, useCallback } from 'react';

interface KeyboardNavOptions {
  onSearchFocus?: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  onSelect?: () => void;
  onClose?: () => void;
  onToggleCommandMenu?: () => void;
  enabled?: boolean;
}

export function useKeyboardNav({
  onSearchFocus,
  onNext,
  onPrev,
  onSelect,
  onClose,
  onToggleCommandMenu,
  enabled = true,
}: KeyboardNavOptions) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      const target = event.target as HTMLElement;
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      // Global Command Palette (Cmd+K / Ctrl+K) works anywhere
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        onToggleCommandMenu?.();
        return;
      }

      // Escape closes open drawer/modal even inside inputs
      if (event.key === 'Escape') {
        onClose?.();
        return;
      }

      // Do not intercept other single keys if user is actively typing in an input
      if (isInput) return;

      // '/' focuses search input
      if (event.key === '/') {
        event.preventDefault();
        onSearchFocus?.();
      }

      // 'j' or Down arrow moves next
      if (event.key === 'j' || event.key === 'ArrowDown') {
        event.preventDefault();
        onNext?.();
      }

      // 'k' or Up arrow moves previous
      if (event.key === 'k' || event.key === 'ArrowUp') {
        event.preventDefault();
        onPrev?.();
      }

      // 'Enter' or 'Space' selects item
      if (event.key === 'Enter') {
        event.preventDefault();
        onSelect?.();
      }
    },
    [enabled, onSearchFocus, onNext, onPrev, onSelect, onClose, onToggleCommandMenu]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
