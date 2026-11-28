for (const divider of document.querySelectorAll("[data-panel-size]")) {
  const layout = divider.closest(".app");
  const panel = document.getElementById(divider.getAttribute("aria-controls"));
  const key = divider.dataset.panelSize;
  const vertical = divider.getAttribute("aria-orientation") === "vertical";
  const reverse = divider.hasAttribute("data-reverse") ? -1 : 1;
  const min = Number(divider.dataset.min);
  const max = () => Math.max(min, Math.floor(Number(divider.dataset.limit) *
    (vertical ? layout.clientWidth : layout.clientHeight)));
  const measure = () => Math.round(vertical ? panel.getBoundingClientRect().width : panel.getBoundingClientRect().height);
  let preferred = null;
  try {
    const saved = Number(localStorage.getItem(key));
    if (saved >= min) preferred = saved;
  } catch {
    // Resizing remains available when browser storage is unavailable.
  }

  function apply() {
    if (preferred !== null) {
      layout.classList.add(`custom-${key}`);
      layout.style.setProperty(`--${key}`, `${Math.max(min, Math.min(max(), preferred))}px`);
    }
    divider.setAttribute("aria-valuemin", String(min));
    divider.setAttribute("aria-valuemax", String(max()));
    divider.setAttribute("aria-valuenow", String(Math.max(min, Math.min(max(), measure()))));
  }

  function setSize(value) {
    preferred = Math.max(min, Math.min(max(), Math.round(value)));
    apply();
  }

  function save() {
    if (preferred === null) return;
    try {
      localStorage.setItem(key, String(preferred));
    } catch {
      // The current layout still applies.
    }
  }

  let drag = null;
  const coordinate = (event) => vertical ? event.clientX : event.clientY;

  divider.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || drag) return;
    event.preventDefault();
    divider.focus();
    drag = { id: event.pointerId, origin: coordinate(event), size: measure() };
    divider.setPointerCapture(event.pointerId);
    layout.classList.add(vertical ? "resizing-columns" : "resizing-rows");
  });
  divider.addEventListener("pointermove", (event) => {
    if (drag?.id === event.pointerId) {
      setSize(drag.size + (coordinate(event) - drag.origin) * reverse);
    }
  });
  divider.addEventListener("lostpointercapture", (event) => {
    if (drag?.id !== event.pointerId) return;
    drag = null;
    layout.classList.remove("resizing-columns", "resizing-rows");
    save();
  });
  divider.addEventListener("keydown", (event) => {
    const decrease = vertical ? "ArrowLeft" : "ArrowUp";
    const increase = vertical ? "ArrowRight" : "ArrowDown";
    if (event.key === decrease || event.key === increase) {
      setSize(measure() + (event.key === increase ? 16 : -16) * reverse);
    } else if (event.key === "Home" || event.key === "End") {
      setSize(event.key === "Home" ? min : max());
    } else {
      return;
    }
    event.preventDefault();
    save();
  });

  new ResizeObserver(apply).observe(layout);
  apply();
}
