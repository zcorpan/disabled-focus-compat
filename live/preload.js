() => {
  let prev = null; try { prev = JSON.parse(sessionStorage.getItem("__dfc") || "null"); } catch {}
  const L = (window.__dfc = { t0: performance.now(), ev: [], prev, url: location.href.replace(/[?#].*/, "") });
  const now = () => Math.round(performance.now() - L.t0);
  const desc = (el) => {
    if (!el || !el.nodeName) return String(el);
    let s = el.nodeName.toLowerCase();
    if (el.id) s += "#" + el.id;
    if (el.name) s += `[name=${String(el.name).slice(0, 30)}]`;
    if (el.type) s += `[type=${el.type}]`;
    return s;
  };
  const frame = () => {
    const st = (new Error().stack || "").split("\n").filter(l => l && !l.includes("__dfc"));
    return (st[2] || st[1] || "").replace(/[?#][^:]*/, "").slice(0, 200);
  };
  const push = (kind, extra) => {
    L.ev.push({ t: now(), kind, active: desc(document.activeElement), ...extra });
    try { sessionStorage.setItem("__dfc", JSON.stringify({ url: L.url, ev: L.ev })); } catch {}
  };
  const focusedInside = (el) => {
    const a = document.activeElement;
    return !!a && (a === el || (el.nodeName === "FIELDSET" || el.nodeName === "FORM") && el.contains(a));
  };
  for (const C of [HTMLButtonElement, HTMLInputElement, HTMLSelectElement, HTMLTextAreaElement, HTMLFieldSetElement]) {
    const d = Object.getOwnPropertyDescriptor(C.prototype, "disabled");
    Object.defineProperty(C.prototype, "disabled", {
      ...d,
      set(v) {
        if (v && !d.get.call(this) && focusedInside(this)) push("disable-focused", { el: desc(this), via: "prop", at: frame() });
        return d.set.call(this, v);
      },
    });
  }
  const setAttr = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function (n, v) {
    if (String(n).toLowerCase() === "disabled" && !this.hasAttribute("disabled") && focusedInside(this)) {
      push("disable-focused", { el: desc(this), via: "attr", at: frame() });
    }
    return setAttr.call(this, n, v);
  };
  const ofetch = window.fetch;
  window.fetch = function (input, init) {
    push("fetch", { url: String(input && input.url || input).replace(/[?#].*/, "").slice(0, 150), at: frame() });
    return ofetch.apply(this, arguments);
  };
  const oopen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u) { this.__dfcUrl = String(u).replace(/[?#].*/, "").slice(0, 150); return oopen.apply(this, arguments); };
  const osend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function () { push("xhr", { url: this.__dfcUrl, at: frame() }); return osend.apply(this, arguments); };
  for (const m of ["submit", "requestSubmit"]) {
    const o = HTMLFormElement.prototype[m];
    HTMLFormElement.prototype[m] = function () { push("form." + m, { el: desc(this), at: frame() }); return o.apply(this, arguments); };
  }
  addEventListener("submit", e => push("submit-event", { el: desc(e.target) }), true);
  addEventListener("keydown", e => { if (e.key === "Enter") push("keydown-enter", { target: desc(e.target), disabled: !!e.target.disabled }); }, true);
  addEventListener("blur", e => { if (e.target !== window && e.target.nodeType === 1) push("blur", { el: desc(e.target) }); }, true);
  addEventListener("beforeunload", () => push("beforeunload", {}), true);
}
