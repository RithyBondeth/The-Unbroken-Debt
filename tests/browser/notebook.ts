import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { notebookMap } from "../../src/ui/notebook/NotebookMap";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import { saveShot } from "../../src/debug/saveShot";

async function review() {
  if (!import.meta.env.DEV) return;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-unified-notebook-qa"),
  });
  game.flags.set("ep1.illustration.inked", true);
  game.inventory.add("sketchbook");
  game.inventory.add("satchel");
  await game.start({ audio: false });
  let previewMap: ReturnType<typeof notebookMap> | null = null;
  const readContent = game.notebookContent.bind(game);
  game.notebookContent = (written) => {
    const content = readContent(written);
    return previewMap
      ? { ...content, map: previewMap, signature: content.signature + JSON.stringify(previewMap) }
      : content;
  };
  const report = document.getElementById("report")!;
  const bookUpdate = game.sketchbook!.update.bind(game.sketchbook);
  let slowTurn = false;
  let holdTurn = false;
  game.sketchbook!.update = (dt) =>
    bookUpdate(
      holdTurn && (game.sketchbook?.turnState?.progress ?? 0) >= 0.47
        ? 0
        : slowTurn
          ? dt * 0.12
          : dt,
    );
  const button = (name: string, fn: () => void | Promise<void>) => {
    const b = document.createElement("button");
    b.textContent = name;
    b.style.cssText =
      "padding:8px;background:#e8dfcb;color:#28251d;border:1px solid #aa9473;cursor:pointer";
    b.onclick = () => {
      void Promise.resolve(fn()).catch((error) => {
        report.textContent = String(error);
      });
    };
    document.getElementById("qa")!.append(b);
  };
  button("Open notebook", () => game.toggleSketchbook());
  button("Collect matchbox", () => {
    game.inventory.add("matches", 10);
    report.textContent = "Matchbox collected. Check the live checklist in either view.";
  });
  button("Record discovery", () => {
    game.closeSketchbook();
    game.sketchbook?.write("SB-01");
    report.textContent = "Production discovery animation: SB-01 opens in the physical book.";
  });
  button("Save notebook", async () => {
    const save = {
      ...newGameSave(),
      flags: {
        ...game.flags.toJSON(),
        "sketchbook.written": [...(game.sketchbook?.written ?? [])].join(","),
      },
      inventory: game.inventory.toJSON(),
    };
    await game.saves.save("slot1", save);
    report.textContent = "Saved notebook to the isolated QA database.";
  });
  button("Restore saved notebook", async () => {
    const { save } = await game.saves.load("slot1");
    if (!save) throw new Error("Save notebook first");
    game.closeSketchbook();
    game.flags.load(save.flags);
    game.inventory.load(save.inventory);
    game.sketchbook?.written.clear();
    game.sketchbook?.restore(
      String(save.flags["sketchbook.written"] ?? "")
        .split(",")
        .filter(Boolean),
    );
    game.toggleSketchbook();
    report.textContent = "Restored saved inventory, objective and discoveries from IndexedDB.";
  });
  for (const [name, map] of [
    ["Studio map", null],
    ["Village map", notebookMap(false, { x: 2, y: 0, z: -15 }, true)],
    ["Approach map", notebookMap(false, { x: 0, y: 0, z: 35 }, false)],
  ] as const)
    button(name, () => {
      previewMap = map;
      if (!game.sketchbook?.isRaised) game.toggleSketchbook();
      game.sketchbook?.showSection("map");
      report.textContent = `${name}: production map renderer with preview coordinates.`;
    });
  button("Slow next page", () => {
    slowTurn = true;
    game.sketchbook?.turn(1);
  });
  button("Hold page turn", () => {
    holdTurn = true;
    slowTurn = false;
    game.sketchbook?.turn(1);
  });
  button("Normal speed", () => {
    holdTurn = false;
    slowTurn = false;
  });
  button("Verify flows", async () => {
    holdTurn = false;
    slowTurn = false;
    previewMap = null;
    const wait = async (test: () => boolean) => {
      const start = performance.now();
      while (!test()) {
        if (performance.now() - start > 10000) throw new Error("Notebook animation timed out");
        await new Promise<void>((resolve) =>
          game.scene.onAfterRenderObservable.addOnce(() => resolve()),
        );
      }
    };
    const check = (condition: unknown, message: string) => {
      if (!condition) throw new Error(message);
    };
    const key = (code: string) => {
      window.dispatchEvent(new KeyboardEvent("keydown", { code, bubbles: true }));
      window.dispatchEvent(new KeyboardEvent("keyup", { code, bubbles: true }));
    };
    const book = game.sketchbook!;
    game.closeSketchbook();
    await wait(() => !book.isVisible);
    key("KeyQ");
    await wait(() => book.isOpen && !book.isBusy);
    check(
      !game.notebook.isOpen && book.book.root.isEnabled(),
      "Q must open only the physical book",
    );
    check(book.section === "now", "Manual opening must show the live objective");
    check(
      book.painter.pages.slice(0, 2).every((p) => p.kind === "map"),
      "The map must occupy both facing pages",
    );
    for (const page of book.painter.pages.filter((p) => p.section === "people")) {
      check(
        new Set(page.layout.blocks.map((b) => b.entryId)).size <= 1,
        "Portrait entries must not share a page",
      );
      for (const placed of page.layout.blocks)
        check(placed.y + placed.height <= 186, "Portrait content must stay inside the page");
    }
    check(game.gated.notebook, "Reading must hold movement and look");
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    const canvas = engine.getRenderingCanvas()!;
    const viewport = game.camera.viewport.toGlobal(canvas.clientWidth, canvas.clientHeight);
    for (const x of [-0.1, 0.1]) {
      const footer = Vector3.Project(
        new Vector3(x, 0.006, -0.093),
        book.book.root.computeWorldMatrix(true),
        game.scene.getTransformMatrix(),
        viewport,
      );
      check(
        footer.y + 8 <
          document.querySelector(".notebook-page-controls")!.getBoundingClientRect().top,
        "Page footer must remain above the action bar",
      );
    }
    key("KeyR");
    await wait(() => game.notebook.isOpen);
    check(!book.book.root.isEnabled(), "Clear reading must hide the physical presentation");
    game.notebook.select("lore");
    game.notebook.back();
    check(
      book.section === "lore" && book.book.root.isEnabled(),
      "Return must preserve the selected section",
    );
    book.turn(-1);
    book.update(0.1);
    key("KeyQ");
    await wait(() => !book.isVisible && !book.isBusy);
    check(
      !game.gated.notebook && !game.notebook.isOpen,
      "Closing during a turn must release the reading gate",
    );
    key("KeyQ");
    await wait(() => book.isOpen && !book.isBusy);
    game.threatActive = true;
    await wait(() => !book.isVisible && !game.gated.notebook);
    key("KeyQ");
    check(!book.isRaised, "An active threat must dismiss the book and prevent reopening");
    game.threatActive = false;
    book.written.delete("SB-01");
    book.write("SB-01");
    await wait(() => book.isOpen && !book.isBusy);
    check(
      book.written.has("SB-01") && book.section === "notes" && !game.notebook.isOpen,
      "Discoveries must stay in the physical book",
    );
    const before = game.notebookContent();
    const saved = {
      ...newGameSave(),
      flags: { ...game.flags.toJSON(), "sketchbook.written": [...book.written].join(",") },
      inventory: game.inventory.toJSON(),
    };
    await game.saves.save("slot1", saved);
    game.inventory.add("matches", 3);
    game.flags.set("ep1.arrival.callComplete", true);
    book.write("L4");
    game.closeSketchbook();
    const loaded = (await game.saves.load("slot1")).save;
    check(loaded, "QA checkpoint must load from IndexedDB");
    game.flags.load(loaded!.flags);
    game.inventory.load(loaded!.inventory);
    book.written.clear();
    book.restore(
      String(loaded!.flags["sketchbook.written"] ?? "")
        .split(",")
        .filter(Boolean),
    );
    check(
      JSON.stringify(game.notebookContent().entries) === JSON.stringify(before.entries),
      "Restore must recover checklist, clues, people and lore together",
    );
    await wait(() => !book.isVisible);
    key("KeyQ");
    key("KeyQ");
    await wait(() => !book.isVisible && !book.isBusy);
    check(!game.gated.notebook, "Q during raising must close cleanly");
    report.textContent =
      "PASS: physical opening, live objective, clear-reading mode, section return, close mid-turn, automatic discovery, rapid Q, threat dismissal, input release, IndexedDB restoration. Saves use isolated QA storage.";
  });
  button("Clean preview", () => {
    document.getElementById("qa")!.hidden = true;
    document.getElementById("qa")!.style.display = "none";
    report.hidden = true;
    for (const node of document.querySelectorAll<HTMLElement>(".perf-overlay")) node.hidden = true;
  });
  button("Save screenshot", async () => {
    await saveShot(engine, game.camera, `notebook-${game.sketchbook?.section ?? "closed"}`);
    report.textContent = `Saved debug-shots/notebook-${game.sketchbook?.section ?? "closed"}.png`;
  });
  report.textContent =
    "Click to begin, then open the notebook. Q: book · R: read clearly · 1–5: sections · A/D: pages · Esc: close.";
}
void review().catch((error) => {
  document.getElementById("report")!.textContent = String(error);
});
