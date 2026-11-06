/** Real production scene + isolated saves. Scripted story inputs are explicit below. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { isQualityName } from "../../src/render/qualityPresets";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import { saveShot } from "../../src/debug/saveShot";
import { ANCESTORS, MIRROR_TARGETS } from "../../src/episodes/ep2/data/pagoda";
import type { WhisperingPagoda } from "../../src/episodes/ep2/WhisperingPagoda";

type View = [number[], number[]];
const VIEWS: Record<string, View> = {
  gate: [
    [0, 0.08, 37],
    [0, 3.9, 27],
  ],
  kuti: [
    [-18, 0.22, 17],
    [-18, 1.1, 11],
  ],
  garden: [
    [-15, 0.08, 12],
    [4, 1.5, -6],
  ],
  offering: [
    [-12, 0.08, 9],
    [-12, 0.7, 6.5],
  ],
  hall: [
    [20, 0.08, 12],
    [22, 3, -1],
  ],
  interior: [
    [22, 0.22, 3.8],
    [22, 2.8, -6],
  ],
  cloister: [
    [-24.5, 0.08, 5],
    [-24.5, 1.7, -12],
  ],
  pond: [
    [0, 0.08, -16],
    [0, 3.5, -32],
  ],
  library: [
    [0, 1.4, -29],
    [0, 2.3, -34],
  ],
  pret: [
    [-14, 0.08, 17.5],
    [-14, 2.6, 12],
  ],
  memory: [
    [80, 0.08, 10],
    [80, 1, -8],
  ],
};
const output = document.getElementById("results")!;
const log = (text: string) => {
  output.textContent += "\n" + text;
};
const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
async function wait(test: () => boolean, label: string, timeout = 15000): Promise<void> {
  const until = performance.now() + timeout;
  while (!test()) {
    if (performance.now() > until) throw new Error("Timed out: " + label);
    await sleep(50);
  }
}
async function boot(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const url = new URL(location.href);
  url.searchParams.set("start", "ep2");
  history.replaceState(null, "", url);
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const device = await detectDevice(),
    quality = url.searchParams.get("quality");
  if (isQualityName(quality)) device.quality = quality;
  const game = new Game(engine, device);
  const saves = new SaveStore(undefined, "boon-sop-ep2-review");
  Object.defineProperty(game, "saves", { value: saves });
  // Reviews start fresh; never read or overwrite the player's database.
  await saves.clear("autosave");
  await saves.clear("checkpoint");
  const reviewSave = newGameSave();
  reviewSave.episode = 2;
  reviewSave.flags = { "ep2.started": true, "ep2.monk.met": true, "ep2.preview": true };
  const scene = url.searchParams.get("scene") ?? "sophal";
  if (scene !== "sophal") {
    reviewSave.flags["ep2.bridge.open"] = true;
    for (const a of ANCESTORS) reviewSave.flags["ep2.offering." + a.id] = true;
  }
  if (scene === "harvest")
    Object.assign(reviewSave.flags, { "ep2.archive.open": true, "ep2.cinematic.harvest": true });
  if (scene === "collapse")
    Object.assign(reviewSave.flags, { "ep2.memory.choice": 2, "ep2.cinematic.collapse": true });
  if (scene === "dawn") Object.assign(reviewSave.flags, { "ep2.escaped": true });
  reviewSave.inventory = { satchel: 1, sketchbook: 1, lamp: 1, matches: 10, oil: 2 };
  reviewSave.lamp = { oil: 1, state: "open" };
  await saves.save("autosave", reviewSave);
  game.fade.waitForEnter = () => Promise.resolve();
  await game.start({ audio: false });
  const act = await (async () => {
    await wait(
      () => !!(window as unknown as { pagoda?: WhisperingPagoda }).pagoda,
      "episode initialization",
    );
    return (window as unknown as { pagoda: WhisperingPagoda }).pagoda;
  })();
  await wait(() => act.active && !game.cutscene, "episode begin");
  await game.fade.to(0, 0);
  game.hints.hide();
  game.subtitles.hide();
  log(
    "Anchors: " +
      act.area.level.interactables
        .filter((m) => /monk|memory_shrine|stupa_chea/.test(m.name))
        .map((m) => m.name + ":" + m.position.toString())
        .join(" / "),
  );
  const look = (view: string) => {
    current = view;
    const [feet, target] = VIEWS[view];
    const at = Vector3.FromArray(feet),
      to = Vector3.FromArray(target);
    game.fallGuard.bounds = view === "memory" ? { minX: 69, maxX: 91, minZ: -16, maxZ: 16 } : null;
    game.player.teleport(at, Math.atan2(to.x - at.x, to.z - at.z));
    game.player.pitch = Math.atan2(at.y + 1.58 - to.y, Math.hypot(to.x - at.x, to.z - at.z));
    game.fallGuard.reset(at);
    game.input.clear();
    log("View: " + view);
  };
  output.textContent =
    "Production Episode 2 · " +
    device.quality +
    " · isolated review saves\nNo audio; ghosts pause without pointer capture.";
  for (const button of document.querySelectorAll<HTMLButtonElement>("[data-view]"))
    button.onclick = () => look(button.dataset.view!);
  log(
    "Anchors: " +
      act.area.level.interactables
        .filter((m) => /monk|memory_shrine|stupa_chea/.test(m.name))
        .map((m) => m.name + ":" + m.position.toString())
        .join(" / "),
  );
  let current = url.searchParams.get("view") ?? "gate";
  if (url.searchParams.has("scene"))
    current =
      scene === "harvest"
        ? "memory"
        : scene === "collapse"
          ? "library"
          : scene === "dawn"
            ? "offering"
            : "kuti";
  if (!(current in VIEWS)) current = "gate";
  look(current);
  const preview = document.getElementById("cinematic") as HTMLButtonElement;
  preview.textContent = "Play " + scene + " cinematic";
  preview.onclick = () => {
    preview.disabled = true;
    const run =
      scene === "harvest"
        ? () => act.cinematics.harvest()
        : scene === "collapse"
          ? () => act.cinematics.breakLibrary()
          : scene === "dawn"
            ? () => act.cinematics.dawn()
            : () => act.cinematics.sophal();
    void run()
      .then(() => log("PASS " + scene + " cinematic completed / skipped"))
      .catch((error) => log("FAIL " + String(error)))
      .finally(() => {
        preview.disabled = false;
      });
  };
  const escapeButton = document.getElementById("escape") as HTMLButtonElement;
  escapeButton.hidden = scene !== "collapse";
  escapeButton.onclick = () => {
    escapeButton.disabled = true;
    const run = async () => {
      const read = game.input.readMove.bind(game.input);
      let moving = false;
      try {
        // The actual destruction sequence finishes before the active escape allowance starts.
        await act.cinematics.breakLibrary();
        act.escapeClock.reset();
        game.player.teleport(new Vector3(0, 1.4, -34), 0);
        game.fallGuard.reset(game.player.feet);
        Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => true });
        game.input.readMove = (out) => {
          out.x = 0;
          out.z = moving ? 1 : 0;
          out.hurry = false;
          out.crouch = false;
          return out;
        };
        const deadline = performance.now() + 85000;
        for (const [x, z] of [
          [0, -17],
          [-14, -17],
          [-14, 8.5],
          [-12, 8.5],
        ]) {
          moving = true;
          while (
            act.progress.stage === "escape" &&
            Math.hypot(game.player.feet.x - x, game.player.feet.z - z) > 0.25
          ) {
            if (performance.now() > deadline)
              throw new Error("Escape blocked at " + game.player.feet.toString());
            game.player.yaw = Math.atan2(x - game.player.feet.x, z - game.player.feet.z);
            await sleep(40);
          }
          moving = false;
          log(
            "Escape waypoint " +
              x +
              "," +
              z +
              " · " +
              act.escapeClock.remaining.toFixed(1) +
              "s left",
          );
          if (act.progress.stage === "dawn") break;
        }
        if (act.progress.stage !== "dawn") throw new Error("Dawn not reached");
        log(
          "PASS PHYSICAL ESCAPE · actual broken roof, shelves, bridge and timer · " +
            act.escapeClock.remaining.toFixed(1) +
            "s margin",
        );
      } finally {
        moving = false;
        game.input.readMove = read;
        Object.defineProperty(game.input, "pointerLocked", {
          configurable: true,
          get: () => false,
        });
      }
    };
    void run().catch((error) => {
      log("FAIL " + String(error));
      console.error(error);
    });
  };
  setInterval(() => {
    const d = act.cinematics.director;
    document.body.dataset.cinematic = d.currentId ?? "none";
    document.body.dataset.sceneTime = d.elapsed.toFixed(2);
    document.body.dataset.scenePaused = String(d.isPaused);
  }, 100);
  log(
    "Cinematic morph meshes: " +
      act.cinematics.area.container.meshes.filter(
        (m) => "morphTargetManager" in m && !!m.morphTargetManager,
      ).length,
  );
  document.getElementById("capture")!.onclick = () => {
    void saveShot(engine, game.camera, "ep2-" + current);
  };
  for (const button of document.querySelectorAll<HTMLButtonElement>("[data-view]"))
    button.addEventListener("click", () => {
      current = button.dataset.view!;
    });
  document.getElementById("clean")!.onclick = () => {
    document.getElementById("review")!.hidden = true;
    output.hidden = true;
  };
  const traversal = async () => {
    document.getElementById("traversal")!.setAttribute("disabled", "");
    document.getElementById("journey")!.setAttribute("disabled", "");
    output.textContent =
      "Real Havok controller + production interaction rays. Threats held during traversal; isolated saves.";
    game.flags.set("ep2.monk.met", true);
    // Open the two real physical gates through their production interactions.
    for (const a of ANCESTORS) game.flags.set("ep2.offering." + a.id, true);
    for (const n of [2, 0, 1]) {
      game.bus.emit("interact:use", { id: "interact_bell_" + n });
      await sleep(180);
    }
    game.bus.emit("interact:use", { id: "interact_bridge_lock" });
    await sleep(250);
    await wait(() => !game.cutscene && !saves.saving, "gate checkpoint");
    const read = game.input.readMove.bind(game.input);
    let moving = false;
    game.input.readMove = (out) => {
      out.x = 0;
      out.z = moving ? 1 : 0;
      out.hurry = false;
      out.crouch = false;
      return out;
    };
    const check = (ok: boolean, text: string) => {
      if (!ok) throw new Error(text);
      log("PASS " + text);
    };
    const walk = async (name: string, from: Vector3, to: Vector3, timeout: number) => {
      game.cutscene = true;
      game.gated.holdStill = false;
      game.player.teleport(from, Math.atan2(to.x - from.x, to.z - from.z));
      game.fallGuard.reset(from);
      const deadline = performance.now() + timeout;
      moving = true;
      try {
        while (Math.hypot(game.player.feet.x - to.x, game.player.feet.z - to.z) > 0.3) {
          if (performance.now() > deadline)
            throw new Error(name + " blocked at " + game.player.feet.toString());
          await sleep(50);
        }
      } finally {
        moving = false;
      }
      await sleep(250);
      check(game.player.supported, name + " · supported at " + game.player.feet.toString());
    };
    try {
      await walk("Naga gate", new Vector3(0, 0.08, 32), new Vector3(0, 0, 24), 10000);
      await walk("Kuti threshold", new Vector3(-18, 0.08, 17.5), new Vector3(-18, 0.2, 14), 6500);
      await walk("Prayer hall threshold", new Vector3(22, 0.08, 9), new Vector3(22, 0.2, 5), 6500);
      await walk("Library bridge ramp", new Vector3(0, 0.08, -17), new Vector3(0, 1.4, -29), 13000);
      check(game.player.feet.y > 1.25, "Bridge climbs continuously to raised library");
      await walk("Library return", new Vector3(0, 1.4, -29), new Vector3(0, 0.08, -17), 13000);
      await walk(
        "West garden aisle",
        new Vector3(-14, 0.08, 12),
        new Vector3(-14, 0.08, -14),
        23000,
      );
      game.cutscene = false;
      const rays: [string, number[], number[]][] = [
        ["interact_monk", [-18, 0.22, 13.2], [-18, 0.5, 12]],
        ["interact_stupa_chea", [-12, 0.08, 8.25], [-12, 0.3, 7.35]],
        ["interact_mirror_0", [-2, 1.4, -28.8], [-2, 2.45, -29.8]],
        ["interact_archive", [0, 1.4, -34], [0, 2, -35]],
      ];
      for (const [id, from, to] of rays) {
        const at = Vector3.FromArray(from),
          target = Vector3.FromArray(to);
        game.player.teleport(at, Math.atan2(target.x - at.x, target.z - at.z));
        game.fallGuard.reset(at);
        game.player.pitch = Math.atan2(
          at.y + 1.58 - target.y,
          Math.hypot(target.x - at.x, target.z - at.z),
        );
        await sleep(350);
        game.interaction.update();
        // Library-stage gating is active after opening the bridge, so NPC and stupa reach
        // are measured against real pick geometry while retaining the production ray length.
        const allow = game.interaction.allow;
        game.interaction.allow = () => true;
        game.interaction.update();
        check(
          game.interaction.focus === id,
          "Interaction ray reaches " + id + " (actual " + game.interaction.focus + ")",
        );
        game.interaction.allow = allow;
      }
      log("PASS TRAVERSAL AND INTERACTION REACH COMPLETE · Reload for a new story journey.");
    } finally {
      moving = false;
      game.input.readMove = read;
      game.cutscene = false;
    }
  };
  document.getElementById("traversal")!.onclick = () => {
    void traversal().catch((error) => {
      log("FAIL " + String(error));
      console.error(error);
    });
  };
  const journey = async () => {
    document.getElementById("journey")!.setAttribute("disabled", "");
    output.textContent =
      "Episode 2 production journey. Story interaction events + real paper controls; player input held for deterministic puzzles.";
    // This puzzle/save test uses the real Skip control. Scene playback is reviewed separately.
    const skipTimer = setInterval(() => {
      for (const button of document.querySelectorAll<HTMLButtonElement>(
        ".cinematic-controls:not([hidden]) button",
      ))
        if (button.textContent === "Skip scene") button.click();
    }, 100);
    try {
      const use = async (id: string) => {
        game.bus.emit("interact:use", { id: "interact_" + id });
        await sleep(80);
      };
      const click = async (label: string) => {
        await wait(
          () =>
            [
              ...document.querySelectorAll<HTMLButtonElement>(".resolution:not([hidden]) button"),
            ].some((b) => b.textContent === label && !b.disabled),
          "button " + label,
        );
        [...document.querySelectorAll<HTMLButtonElement>(".resolution:not([hidden]) button")]
          .find((b) => b.textContent === label)!
          .click();
        await sleep(80);
      };
      const idle = () => wait(() => !game.cutscene && !saves.saving, "save/dialog completion");
      const check = (ok: boolean, text: string) => {
        if (!ok) throw new Error(text);
        log("PASS " + text);
      };
      game.flags.load({
        "ep2.started": true,
        "ep2.preview": true,
        "ep2.checkpoint": "CP0",
        "ep1.complete": true,
        "ep1.journal.shared": false,
        "lore.ep1.L3": true,
        "series.respect": 2,
        "game.run": "ep2-browser-review",
      });
      game.inventory.load({
        satchel: 1,
        sketchbook: 1,
        lamp: 1,
        matches: 10,
        oil: 2,
        seal_map: 1,
        sok_journal: 1,
      });
      // An independently stored Episode 1 completion must survive the entire episode.
      const previous = newGameSave();
      Object.assign(previous.flags, {
        "ep1.complete": true,
        "ep1.journal.shared": false,
        "series.respect": 2,
      });
      await saves.save("episode1", previous);
      // Reject the first checkpoint write; retry through the production failure UI.
      const mark = saves.saveCheckpoint.bind(saves);
      let reject = true;
      saves.saveCheckpoint = async (save) => {
        if (reject) {
          reject = false;
          throw new Error("Injected quota failure");
        }
        await mark(save);
      };
      await use("monk");
      await click("Receive the white thread");
      await click("Retry save");
      await idle();
      check(act.progress.stage === "garden", "Monk guidance and failed checkpoint retry");
      await use("lore_monk");
      await click("Copy into the sketchbook");
      await idle();
      for (const item of ["rice", "lotus", "water", "bowls"]) {
        await use("pickup_" + item);
        await idle();
      }
      // One wrong offering must leave the rice supply and other puzzle items intact.
      await use("stupa_chea");
      await click("Offer a lotus bud");
      await click("Read the inscription again");
      await idle();
      check(game.inventory.count("lotus") === 1, "Wrong offering keeps required resources");
      for (const a of ANCESTORS) {
        await use("stupa_" + a.id);
        await click(
          a.item === "rice"
            ? "Offer rice balls"
            : a.item === "lotus"
              ? "Offer a lotus bud"
              : "Offer sanctified water",
        );
        await idle();
      }
      check(
        act.progress.offerings === 4 && act.progress.pretCount === 5,
        "Four offerings escalate to five Pret",
      );
      for (const n of [2, 0, 1]) {
        await use("bell_" + n);
        await idle();
      }
      for (const id of ["hall_0", "hall_1"]) {
        await use("lore_" + id);
        await click("Copy into the sketchbook");
        await idle();
      }
      check(game.flags.get("ep2.hall.open", false), "Optional bells release the prayer hall");
      await use("bridge_lock");
      await idle();
      for (let i = 0; i < MIRROR_TARGETS.length; i++)
        for (let n = 0; n < MIRROR_TARGETS[i]; n++) {
          await use("mirror_" + i);
          await idle();
        }
      for (const id of ["library_0", "library_1"]) {
        await use("lore_" + id);
        await click("Copy into the sketchbook");
        await idle();
      }
      check(
        act.progress.mirrorsAligned && act.progress.lore.length === 5,
        "Moonbeam puzzle and five saved lore notes",
      );
      await use("archive");
      await click("Enter Chea’s memory");
      await idle();
      check(
        act.progress.stage === "memory" && game.player.feet.x > 69,
        "Playable forest memory loads outside present-day pagoda",
      );
      await use("memory_shrine");
      await click("Save my children… and let us never be poor again.");
      await click("Return to the library");
      await idle();
      check(act.progress.stage === "escape", "Truthful choice returns Sora to collapsing library");
      // Deterministic escape destination; the separate movement check covers bridge physics.
      Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => true });
      game.player.teleport(new Vector3(-12, 0.08, 8.5), Math.PI);
      log(
        "Escape diagnostic: " +
          JSON.stringify({
            paused: act.paused,
            hidden: document.hidden,
            pointer: game.input.pointerLocked,
            feet: game.player.feet.toString(),
            stage: act.progress.stage,
          }),
      );
      await wait(() => act.progress.stage === "dawn", "escape to dawn", 15000);
      await idle();
      Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => false });
      check(act.progress.stage === "dawn", "Escape reaches the dawn checkpoint");
      await use("stupa_chea");
      await click("Speak their names");
      for (const a of ANCESTORS) await click(a.name);
      await click("Three nights remain");
      await wait(() => act.progress.stage === "complete", "episode completion");
      const saved = (await saves.load("episode2")).save;
      check(
        saved?.episode === 2 && saved.flags["ep2.seal2.broken"] === true,
        "Separate Episode 2 completion archive",
      );
      check(
        saved?.flags["ep1.journal.shared"] === false &&
          saved.flags["lore.ep1.L3"] === true &&
          saved.flags["series.respect"] === 5,
        "Episode 1 choice, lore and respect survive",
      );
      check(
        JSON.stringify((await saves.load("episode1")).save) === JSON.stringify(previous),
        "Episode 1 archive untouched",
      );
      check(
        saved?.inventory.silver_inlay === 1 &&
          saved.inventory.clinic_photo === 1 &&
          saved.inventory.blessed_thread === 1,
        "Second seal, photograph and white thread retained",
      );
      log("PASS EPISODE 2 JOURNEY COMPLETE");
    } finally {
      clearInterval(skipTimer);
    }
  };
  document.getElementById("journey")!.onclick = () => {
    void journey().catch((error) => {
      log("FAIL " + String(error));
      console.error(error);
    });
  };
}
window.addEventListener("error", (e) => log("ERROR " + e.message));
window.addEventListener("unhandledrejection", (e) => log("REJECTION " + String(e.reason)));
void boot().catch((error) => {
  log("FAIL " + String(error));
  console.error(error);
});
