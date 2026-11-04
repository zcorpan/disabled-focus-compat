() => {
  // Variant: while the focused element is an actually disabled form control, key events go to
  // the body (as they did when focus moved there) instead of the disabled control.
  const CONTROLS = new Set(["BUTTON", "INPUT", "SELECT", "TEXTAREA"]);
  for (const type of ["keydown", "keypress", "keyup"]) {
    window.addEventListener(type, e => {
      const t = e.target;
      if (!e.isTrusted || !t || !CONTROLS.has(t.nodeName) || !t.matches(":disabled") || document.activeElement !== t) return;
      e.stopImmediatePropagation();
      const init = {};
      for (const k of ["key", "code", "location", "ctrlKey", "shiftKey", "altKey", "metaKey", "repeat", "isComposing", "charCode", "keyCode", "which"]) init[k] = e[k];
      const clone = new KeyboardEvent(type, { ...init, bubbles: true, cancelable: true, composed: true });
      for (const k of ["keyCode", "which", "charCode"]) Object.defineProperty(clone, k, { value: e[k] });
      document.body && document.body.dispatchEvent(clone);
    }, true);
  }
}
