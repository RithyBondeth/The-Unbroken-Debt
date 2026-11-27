import "@/ui/html/villagePuzzle.css";
import {
  WARD_STATIONS,
  type IncenseCount,
  type WardOfferingId,
  type WardStationId,
} from "../data/villagePuzzles";

const OFFERING_META: Record<WardOfferingId, { label: string; sub: string; icon: string }> = {
  well_water: {
    label: "Bowl of Well Water",
    sub: "Drawn cool from the brick shaft",
    icon: "◠",
  },
  sacred_thread: {
    label: "White Cotton Thread",
    sub: "Undyed sai sin skein",
    icon: "◎",
  },
  ward_marigold: {
    label: "Marigold Phan Dish",
    sub: "Fresh golden blossoms",
    icon: "❀",
  },
};

export interface PadlockClueItem {
  shop: string;
  found: boolean;
  text: string;
}

/**
 * Tactile, museum-grade diegetic puzzle modals & well-tension HUD for Episode 1 Village:
 * - Puzzle 1: Mechanical 3-Dial Brushed Brass Gate Padlock (roller drums + clue strip + keyboard support)
 * - Puzzle 2: Diegetic Brick Well Rope-Strain HUD during `tug_danger`
 * - Puzzle 3: Khmer Ancestral Ward Altar Rite (offering cards + visual incense stick selector)
 * - Puzzle 4: Interactive 1930s Enamel Roman-Numeral Analog Pendulum Clock Dial
 */
export class VillagePuzzleUi {
  private readonly root = document.createElement("div");
  private readonly panel = document.createElement("div");
  private readonly tensionRoot = document.createElement("div");
  private readonly tensionLabel = document.createElement("p");
  private readonly tensionBarFill = document.createElement("div");
  private onClose: (() => void) | null = null;
  private modalKeyHandler: ((e: KeyboardEvent) => void) | null = null;
  private readonly abort = new AbortController();

  constructor() {
    this.root.className = "vp-overlay";
    this.root.hidden = true;
    this.root.setAttribute("role", "dialog");
    this.root.setAttribute("aria-modal", "true");
    this.panel.className = "vp-panel";
    this.root.append(this.panel);
    document.body.append(this.root);

    // Diegetic well-tug tension HUD (non-blocking bottom banner)
    this.tensionRoot.className = "vp-tension";
    this.tensionRoot.hidden = true;
    this.tensionLabel.className = "vp-tension-label";
    const track = el("div", "vp-tension-track");
    this.tensionBarFill.className = "vp-tension-fill";
    track.append(this.tensionBarFill);
    this.tensionRoot.append(this.tensionLabel, track);
    document.body.append(this.tensionRoot);

    window.addEventListener(
      "keydown",
      (e) => {
        if (!this.isOpen) return;
        if (e.code === "Escape") {
          e.preventDefault();
          this.close();
          return;
        }
        this.modalKeyHandler?.(e);
      },
      { signal: this.abort.signal },
    );
  }

  get isOpen(): boolean {
    return !this.root.hidden;
  }

  /** Updates the non-blocking brick well rope-tug tension indicator during `tug_danger`. */
  setWellTension(active: boolean, progress: number, text: string, danger: boolean): void {
    this.tensionRoot.hidden = !active;
    if (!active) return;
    this.tensionLabel.textContent = text;
    this.tensionRoot.classList.toggle("vp-tension-danger", danger);
    this.tensionBarFill.style.width = `${Math.round(Math.max(0, Math.min(1, progress)) * 100)}%`;
  }

  close(): void {
    if (!this.isOpen) return;
    this.root.hidden = true;
    this.modalKeyHandler = null;
    const cb = this.onClose;
    this.onClose = null;
    cb?.();
  }

  dispose(): void {
    this.abort.abort();
    this.root.remove();
    this.tensionRoot.remove();
  }

  /** Puzzle 1: Mechanical 3-Dial Brushed Brass Gate Padlock. */
  openGatePadlock(opts: {
    initial: [number, number, number];
    clueItems: PadlockClueItem[];
    onTick: () => void;
    onTry: (digits: [number, number, number]) => { ok: boolean; message: string };
    onClose: () => void;
  }): void {
    const digits: [number, number, number] = [...opts.initial];
    let activeWheel = 0;
    this.panel.replaceChildren();
    this.panel.className = "vp-panel vp-panel-padlock";

    const eyebrow = el("p", "vp-eyebrow", "Compound Gate · Rusted Brass Padlock");
    const title = el("h2", "vp-title", "Three-Tumbler Lock");

    // Clue ledger strip showing investigated vs unvisited roadside shops
    const clueList = el("div", "vp-clue-strip");
    for (const c of opts.clueItems) {
      const chip = el("div", `vp-clue-chip ${c.found ? "vp-clue-found" : "vp-clue-missing"}`);
      chip.append(
        el("span", "vp-clue-shop", `${c.found ? "✓" : "○"} ${c.shop}`),
        el("span", "vp-clue-note", c.found ? c.text : "Not yet inspected"),
      );
      clueList.append(chip);
    }

    // Physical brass padlock body + steel U-shackle + 3 knurled roller drums
    const lockFrame = el("div", "vp-padlock-body");
    const shackle = el("div", "vp-padlock-shackle");
    const dialsRow = el("div", "vp-dials");
    const labels = ["I · Calendar", "II · Knocks", "III · Lot"];
    const wheelBoxes: HTMLElement[] = [];
    const renderers: (() => void)[] = [];

    const updateSelection = () => {
      wheelBoxes.forEach((b, idx) => b.classList.toggle("vp-dial-active", idx === activeWheel));
    };

    for (let i = 0; i < 3; i++) {
      const box = el("div", "vp-dial vp-dial-brass");
      box.addEventListener("click", () => {
        activeWheel = i;
        updateSelection();
      });
      box.append(el("span", "vp-dial-label", labels[i]));

      const drum = el("div", "vp-drum");
      const prevEl = el("span", "vp-drum-ghost");
      const curEl = el("span", "vp-drum-current");
      const nextEl = el("span", "vp-drum-ghost");
      drum.append(prevEl, curEl, nextEl);

      const renderWheel = () => {
        const d = digits[i];
        prevEl.textContent = String((d + 9) % 10);
        curEl.textContent = String(d);
        nextEl.textContent = String((d + 1) % 10);
      };
      renderWheel();
      renderers.push(renderWheel);

      const stepUp = () => {
        activeWheel = i;
        updateSelection();
        digits[i] = (digits[i] + 1) % 10;
        renderWheel();
        opts.onTick();
      };
      const stepDown = () => {
        activeWheel = i;
        updateSelection();
        digits[i] = (digits[i] + 9) % 10;
        renderWheel();
        opts.onTick();
      };

      const btns = el("div", "vp-step-row");
      btns.append(btn("vp-step", "−", stepDown), btn("vp-step", "+", stepUp));
      box.append(drum, btns);
      wheelBoxes.push(box);
      dialsRow.append(box);
    }
    updateSelection();
    lockFrame.append(dialsRow);

    const status = el("p", "vp-status", "");
    const hintKey = el(
      "p",
      "vp-kbd-hint",
      "Tip: Use ←/→ & ↑/↓ or type 0–9 · Enter to pull shackle",
    );

    const tryUnlock = () => {
      const res = opts.onTry([...digits] as [number, number, number]);
      status.textContent = res.message;
      if (res.ok) {
        this.close();
      } else {
        lockFrame.classList.remove("vp-shake");
        void lockFrame.offsetWidth;
        lockFrame.classList.add("vp-shake");
      }
    };

    const actions = el("div", "vp-actions");
    const cancel = btn("ui-button", "Step back", () => this.close());
    const confirm = btn("ui-button ui-button-primary", "Pull shackle", tryUnlock);
    actions.append(cancel, confirm);

    this.modalKeyHandler = (e) => {
      if (e.code === "ArrowLeft") {
        e.preventDefault();
        activeWheel = (activeWheel + 2) % 3;
        updateSelection();
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        activeWheel = (activeWheel + 1) % 3;
        updateSelection();
      } else if (e.code === "ArrowUp") {
        e.preventDefault();
        digits[activeWheel] = (digits[activeWheel] + 1) % 10;
        renderers[activeWheel]();
        opts.onTick();
      } else if (e.code === "ArrowDown") {
        e.preventDefault();
        digits[activeWheel] = (digits[activeWheel] + 9) % 10;
        renderers[activeWheel]();
        opts.onTick();
      } else if (e.key >= "0" && e.key <= "9") {
        e.preventDefault();
        digits[activeWheel] = Number(e.key);
        renderers[activeWheel]();
        opts.onTick();
        activeWheel = Math.min(2, activeWheel + 1);
        updateSelection();
      } else if (e.code === "Enter") {
        e.preventDefault();
        tryUnlock();
      }
    };

    this.panel.append(eyebrow, title, clueList, shackle, lockFrame, status, hintKey, actions);
    this.show(opts.onClose);
    confirm.focus();
  }

  /** Puzzle 3: Four-Direction Ancestral Ward Station Offering & Incense Count. */
  openWardStation(opts: {
    stationId: WardStationId;
    availableOfferings: WardOfferingId[];
    solvedCount: number;
    onSelectSound: () => void;
    onCommit: (
      offering: WardOfferingId,
      incense: IncenseCount,
    ) => { ok: boolean; message: string; closeAfter?: boolean };
    onClose: () => void;
  }): void {
    const spec = WARD_STATIONS.find((s) => s.id === opts.stationId);
    if (!spec) return;
    let selectedOffering: WardOfferingId | null = opts.availableOfferings[0] ?? null;
    let selectedIncense: IncenseCount = 3;

    this.panel.replaceChildren();
    this.panel.className = "vp-panel vp-panel-ward";

    const eyebrow = el(
      "p",
      "vp-eyebrow",
      `Compound Ward · ${opts.solvedCount} of ${WARD_STATIONS.length} Restored`,
    );
    const title = el("h2", "vp-title", spec.name);
    const inscription = el("blockquote", "vp-inscription", spec.hint);
    const status = el("p", "vp-status", "");

    const offGroup = el("div", "vp-group");
    offGroup.append(el("span", "vp-dial-label", "1. Place Ritual Offering"));
    const offGrid = el("div", "vp-choice-grid");
    const offButtons: { id: WardOfferingId; node: HTMLButtonElement }[] = [];
    for (const id of ["well_water", "sacred_thread", "ward_marigold"] as WardOfferingId[]) {
      const has = opts.availableOfferings.includes(id);
      const meta = OFFERING_META[id];
      const b = document.createElement("button");
      b.type = "button";
      b.className = "vp-choice vp-choice-card";
      b.disabled = !has;
      b.setAttribute("aria-pressed", String(id === selectedOffering));
      b.append(
        el("span", "vp-choice-icon", meta.icon),
        el("span", "vp-choice-title", meta.label),
        el("span", "vp-choice-sub", has ? meta.sub : "Not carried"),
      );
      b.addEventListener("click", () => {
        selectedOffering = id;
        opts.onSelectSound();
        for (const item of offButtons)
          item.node.setAttribute("aria-pressed", String(item.id === selectedOffering));
      });
      offButtons.push({ id, node: b });
      offGrid.append(b);
    }
    offGroup.append(offGrid);

    const incGroup = el("div", "vp-group");
    incGroup.append(el("span", "vp-dial-label", "2. Light Incense Sticks"));
    const incGrid = el("div", "vp-choice-grid");
    const incButtons: { n: IncenseCount; node: HTMLButtonElement }[] = [];
    const incSpecs: { n: IncenseCount; sticks: string; title: string; sub: string }[] = [
      { n: 1, sticks: "│", title: "1 Stick", sub: "Unquiet wandering dead" },
      { n: 2, sticks: "│ │", title: "2 Sticks", sub: "Incomplete offering" },
      { n: 3, sticks: "│ │ │", title: "3 Sticks", sub: "Sacred guardians & elders" },
    ];
    for (const s of incSpecs) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "vp-choice vp-choice-card";
      b.setAttribute("aria-pressed", String(s.n === selectedIncense));
      b.append(
        el("span", "vp-choice-sticks", s.sticks),
        el("span", "vp-choice-title", s.title),
        el("span", "vp-choice-sub", s.sub),
      );
      b.addEventListener("click", () => {
        selectedIncense = s.n;
        opts.onSelectSound();
        for (const item of incButtons)
          item.node.setAttribute("aria-pressed", String(item.n === selectedIncense));
      });
      incButtons.push({ n: s.n, node: b });
      incGrid.append(b);
    }
    incGroup.append(incGrid);

    const actions = el("div", "vp-actions");
    const cancel = btn("ui-button", "Leave", () => this.close());
    const confirm = btn("ui-button ui-button-primary", "Place & light", () => {
      if (!selectedOffering) {
        status.textContent = "I have no offering to place here yet.";
        return;
      }
      const res = opts.onCommit(selectedOffering, selectedIncense);
      status.textContent = res.message;
      if (res.ok || res.closeAfter) this.close();
    });
    actions.append(cancel, confirm);

    this.panel.append(eyebrow, title, inscription, offGroup, incGroup, status, actions);
    this.show(opts.onClose);
    confirm.focus();
  }

  /** Puzzle 4: Interactive 1930s Colonial Wall Pendulum Clock (`20:12` Motif). */
  openHallClock(opts: {
    initialHour: number;
    initialMinute: number;
    clues: string[];
    onTick: (hour: number, minute: number) => void;
    onConfirm: (
      hour: number,
      minute: number,
    ) => {
      ok: boolean;
      closeAfter?: boolean;
      message: string;
    };
    onClose: () => void;
  }): void {
    let hour = ((opts.initialHour % 24) + 24) % 24;
    let minute = ((opts.initialMinute % 60) + 60) % 60;
    const fmt = (n: number) => String(n).padStart(2, "0");

    this.panel.replaceChildren();
    this.panel.className = "vp-panel vp-panel-clock";

    const eyebrow = el("p", "vp-eyebrow", "Hall Pendulum Clock · Phnom Penh 1932");
    const title = el("h2", "vp-title", "Set the Vigil Hour");

    // Live interactive antique enamel Roman-numeral analog clock face
    const clockWrap = el("div", "vp-clock-stage");
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 200 200");
    svg.setAttribute("class", "vp-clock-svg");
    svg.setAttribute("aria-hidden", "true");

    const addSvg = (tag: string, attrs: Record<string, string>) => {
      const node = document.createElementNS(svgNS, tag);
      for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
      svg.append(node);
      return node;
    };
    addSvg("circle", {
      cx: "100",
      cy: "100",
      r: "94",
      fill: "#1f1912",
      stroke: "#b7914a",
      "stroke-width": "6",
    });
    addSvg("circle", {
      cx: "100",
      cy: "100",
      r: "86",
      fill: "#dfd1b0",
      stroke: "#3a2a1b",
      "stroke-width": "1.5",
    });
    addSvg("circle", {
      cx: "100",
      cy: "100",
      r: "78",
      fill: "none",
      stroke: "#3a2a1b",
      "stroke-width": "0.8",
    });

    for (let m = 0; m < 60; m++) {
      const a = (m / 60) * Math.PI * 2 - Math.PI / 2;
      const r0 = m % 5 === 0 ? 74 : 79;
      const r1 = 84;
      addSvg("line", {
        x1: String(100 + Math.cos(a) * r0),
        y1: String(100 + Math.sin(a) * r0),
        x2: String(100 + Math.cos(a) * r1),
        y2: String(100 + Math.sin(a) * r1),
        stroke: "#231a12",
        "stroke-width": m % 5 === 0 ? "2.2" : "0.9",
      });
    }
    const romans = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"];
    romans.forEach((rn, idx) => {
      const a = (idx / 12) * Math.PI * 2 - Math.PI / 2;
      const txt = addSvg("text", {
        x: String(100 + Math.cos(a) * 61),
        y: String(100 + Math.sin(a) * 61 + 4),
        "text-anchor": "middle",
        fill: "#231910",
        "font-family": "Georgia, serif",
        "font-size": "12",
        "font-weight": "bold",
      });
      txt.textContent = rn;
    });

    const hourLine = addSvg("line", {
      x1: "100",
      y1: "108",
      x2: "100",
      y2: "56",
      stroke: "#1c1510",
      "stroke-width": "4.5",
      "stroke-linecap": "round",
    });
    const minLine = addSvg("line", {
      x1: "100",
      y1: "112",
      x2: "100",
      y2: "36",
      stroke: "#2d1a10",
      "stroke-width": "2.6",
      "stroke-linecap": "round",
    });
    addSvg("circle", {
      cx: "100",
      cy: "100",
      r: "5",
      fill: "#b7914a",
      stroke: "#231910",
      "stroke-width": "1.5",
    });
    clockWrap.append(svg);

    const periodTag = el("span", "vp-clock-period", "");
    const hVal = el("div", "vp-dial-value", fmt(hour));
    const mVal = el("div", "vp-dial-value", fmt(minute));

    const renderClock = () => {
      hVal.textContent = fmt(hour);
      mVal.textContent = fmt(minute);
      periodTag.textContent =
        hour === 0
          ? "Midnight Watch (AM)"
          : hour < 5
            ? "Past Midnight (Night Watch)"
            : hour < 12
              ? "Morning"
              : hour < 18
                ? "Afternoon"
                : "Evening Watch (PM)";
      const hDeg = ((hour % 12) + minute / 60) * 30;
      const mDeg = minute * 6;
      hourLine.setAttribute("transform", `rotate(${hDeg} 100 100)`);
      minLine.setAttribute("transform", `rotate(${mDeg} 100 100)`);
    };
    renderClock();

    const stepClock = (dh: number, dm: number) => {
      hour = (hour + dh + 24) % 24;
      minute = (minute + dm + 60) % 60;
      renderClock();
      opts.onTick(hour, minute);
    };

    const row = el("div", "vp-dials vp-dials-clock");
    const hBox = el("div", "vp-dial");
    hBox.append(el("span", "vp-dial-label", "Hour (00–23)"), hVal);
    const hBtns = el("div", "vp-step-row");
    hBtns.append(
      btn("vp-step", "−1", () => stepClock(-1, 0)),
      btn("vp-step", "+1", () => stepClock(1, 0)),
    );
    hBox.append(hBtns);

    const colon = el("div", "vp-colon", ":");

    const mBox = el("div", "vp-dial");
    mBox.append(el("span", "vp-dial-label", "Minute (00–59)"), mVal);
    const mBtns = el("div", "vp-step-row");
    mBtns.append(
      btn("vp-step", "−6", () => stepClock(0, -6)),
      btn("vp-step", "−1", () => stepClock(0, -1)),
      btn("vp-step", "+1", () => stepClock(0, 1)),
      btn("vp-step", "+6", () => stepClock(0, 6)),
    );
    mBox.append(mBtns);
    row.append(hBox, colon, mBox);

    const clueBox = el("ul", "vp-clock-clues");
    for (const line of opts.clues) {
      clueBox.append(el("li", "", line));
    }

    const status = el("p", "vp-status", "");
    const actions = el("div", "vp-actions");
    const cancel = btn("ui-button", "Step back", () => this.close());
    const confirm = btn("ui-button ui-button-primary", "Strike chime", () => {
      const res = opts.onConfirm(hour, minute);
      status.textContent = res.message;
      if (res.ok || res.closeAfter) this.close();
    });
    actions.append(cancel, confirm);

    this.panel.append(eyebrow, title, clockWrap, periodTag, row, clueBox, status, actions);
    this.show(opts.onClose);
    confirm.focus();
  }

  private show(onClose: () => void): void {
    this.onClose = onClose;
    this.root.hidden = false;
  }
}

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function btn(className: string, label: string, onClick: () => void): HTMLButtonElement {
  const b = document.createElement("button");
  b.type = "button";
  b.className = className;
  b.textContent = label;
  b.addEventListener("click", onClick);
  return b;
}
