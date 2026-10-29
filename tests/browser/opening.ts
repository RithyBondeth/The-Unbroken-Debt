/** Isolated browser fixture. Only setup/views are scripted; gameplay and saving use production code. */
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { saveShot } from "../../src/debug/saveShot";
import type { TaxiRide } from "../../src/episodes/ep1/travel/TaxiRide";
import { SAVE_SHRINE_POSITION, SAVE_SHRINE_APPROACH } from "../../src/episodes/ep1/data/saveShrine";
const output = document.getElementById("results")!,
  nav = document.getElementById("controls")!;
const button = (label: string, action: () => void) => {
  const b = document.createElement("button");
  b.textContent = label;
  b.onclick = action;
  b.style.cssText = "padding:8px 12px;background:#d8ceb3;color:#211d17;cursor:pointer";
  nav.append(b);
};
async function boot() {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search),
    stage = params.get("stage") ?? "studio";
  const saves = new SaveStore(undefined, "boon-sop-opening-qa");
  if (!params.has("continue")) {
    sessionStorage.removeItem("boon-sop-opening-qa.taxi-lines");
    const data = newGameSave();
    data.flags = { "game.run": crypto.randomUUID(), "ep1.opening.version": 2 };
    if (stage !== "studio") {
      Object.assign(data.flags, {
        "ep1.illustration.inked": true,
        "ep1.phone.answered": true,
        "ep1.clock.stopped": "20:12",
        "sketchbook.written": "SB-01",
      });
      data.inventory = { satchel: 1, sketchbook: 1, lamp: 1, letters: 1, matches: 10 };
      if (stage === "taxi")
        Object.assign(data.flags, {
          "ep1.travel.pending": true,
          "ep1.travel.elapsed": Number(params.get("elapsed") ?? 0),
          "checkpoint.location": "Taxi · Departing Phnom Penh",
        });
      else {
        data.checkpoint = "CP1";
        data.clock = "23:30";
        Object.assign(data.flags, {
          "ep1.checkpoint": "CP1",
          "ep1.travel.complete": true,
          "ep1.early.required": true,
          "ep1.arrival.road": true,
          "checkpoint.location": "Village · Flooded road",
        });
      }
    }
    await saves.saveCheckpoint(data);
    const url = new URL(location.href);
    url.searchParams.set("continue", "");
    history.replaceState(null, "", url);
  }
  const conversationTrace: string[] = JSON.parse(
    sessionStorage.getItem("boon-sop-opening-qa.taxi-lines") ?? "[]",
  ) as string[];
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", { value: saves });
  await game.start();
  const taxi = (window as unknown as { taxi?: TaxiRide }).taxi;
  if (taxi) {
    let inspectionTime: number | null = null;
    let view = "road";
    if (params.has("review"))
      game.scene.onBeforeRenderObservable.add(() => {
        if (inspectionTime !== null) taxi.elapsed = inspectionTime;
        if (taxi.elapsed > 56) taxi.elapsed = 8;
      });
    for (const [name, yaw, pitch] of [
      ["Road", 0, 0.025],
      ["Dashboard", -0.4, 0.29],
      ["Driver", -1.12, 0.08],
      ["Passenger window", 1.2, 0.02],
      ["Rear cabin", Math.PI, 0.05],
      ["Footwell", 0.18, 1.02],
      ["Sora legs", 0, 1.12],
      ["Lower door", 1.55, 0.72],
    ] as const)
      button(name, () => {
        view = name.toLowerCase().replaceAll(" ", "-");
        inspectionTime = null;
        game.player.yaw = yaw;
        game.player.pitch = pitch;
      });
    if (params.has("review"))
      button("Lightning detail", () => {
        view = "lightning";
        inspectionTime = 37.8;
        game.player.yaw = -0.12;
        game.player.pitch = 0.025;
      });
    const captureStatus = document.createElement("output");
    captureStatus.setAttribute("aria-live", "polite");
    nav.append(captureStatus);
    button("Save screenshot", () => {
      engine.setSize(1600, 1000);
      void saveShot(engine, game.camera, `taxi-${view}`)
        .then(() => {
          captureStatus.textContent = `Saved debug-shots/taxi-${view}.png`;
        })
        .catch((error) => {
          captureStatus.textContent = `Capture failed: ${String(error)}`;
        })
        .finally(() => engine.resize());
    });
    button("Hide review overlays", () => {
      nav.style.display = "none";
      output.hidden = true;
      const perf = document.querySelector<HTMLElement>(".perf-overlay");
      if (perf) perf.style.display = "none";
    });
  }
  button("Notebook Q", () => window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyQ" })));
  button("Reload saved game", () => location.reload());
  const act = (window as unknown as { act?: ActOne }).act;
  if (act) {
    button("Keep the vigil (later obstacle)", () => {
      for (const flag of [
        "ep1.vigil.started",
        "ep1.betel.done",
        "ep1.incense.cyclePassed",
        "ep1.arrival.matchesTaken",
      ])
        game.flags.set(flag, true);
      game.player.teleport(new Vector3(0, 0, -2), 0);
      game.player.pitch = 0.05;
    });
    button("Ghost view", () => {
      game.player.teleport(new Vector3(0, 0, 17), Math.PI);
      game.player.pitch = 0.02;
    });
    button("Trigger a real catch", () => {
      game.inventory.add("matches", 2);
      game.flags.set("qa.afterCheckpoint", true);
      game.player.teleport(
        act.early.brain.position.add(act.early.brain.direction.scale(0.6)),
        Math.PI,
      );
      game.gated.holdStill = true;
    });
    button("Reach safe courtyard", () => {
      game.notebook.close();
      game.gated.holdStill = false;
      game.player.teleport(new Vector3(0, 0, 6), Math.PI);
    });
    button("Aim phra phum save shrine", () => {
      game.notebook.close();
      game.player.teleport(SAVE_SHRINE_APPROACH, Math.PI);
      game.scene.onAfterRenderObservable.addOnce(() =>
        game.inspectObject(SAVE_SHRINE_POSITION.add(new Vector3(0, 1.55, 0.3)), 0.9),
      );
    });
  }
  game.scene.onAfterRenderObservable.add(() => {
    const feet = game.player.feet,
      last = game.checkpoints.last;
    const road = taxi ? game.scene.meshes.find((m) => m.material?.name === "M_wet_mud") : null;
    output.textContent = `Isolated QA database; ${game.resumedSave?.checkpoint} · ${game.flags.get("ep1.travel.pending", false) ? "TAXI" : game.flags.get("ep1.checkpoint", "CP0")}\nCheckpoint: ${last?.flags["checkpoint.location"] ?? last?.checkpoint} · matches ${game.inventory.count("matches")} · post-checkpoint flag ${game.flags.get("qa.afterCheckpoint", false)}\nFeet ${feet.x.toFixed(1)},${feet.y.toFixed(1)},${feet.z.toFixed(1)} · target ${game.interaction.focus ?? "none"}\n${act ? `Passage required=${act.early.required} active=${act.early.active} brain=${act.early.brain.state} at=${act.early.brain.position.toString()} time=${act.early.brain.elapsed.toFixed(1)} threat=${game.threatActive} sight=${act.early.canSeeSora()} suspicion=${act.early.brain.suspicion.toFixed(2)} · passage survived=${game.flags.get("ep1.early.complete", false)}` : ""}`;
    const spoken = document.querySelector(".story-subtitles:not([hidden])")?.textContent?.trim();
    if (taxi && spoken && !conversationTrace.some((line) => line.endsWith(spoken))) {
      conversationTrace.push(`${taxi.elapsed.toFixed(1)}s ${spoken}`);
      sessionStorage.setItem("boon-sop-opening-qa.taxi-lines", JSON.stringify(conversationTrace));
    }
    if (conversationTrace.length)
      output.textContent += `\nTaxi replies observed: ${conversationTrace.length}/14`;
    if (act && conversationTrace.length) output.textContent += `\n${conversationTrace.join("\n")}`;
    if (taxi)
      output.textContent += `\nTaxi ${taxi.elapsed.toFixed(1)}s · road lights ${road?.lightSources.map((l) => `${l.name}:${l.intensity.toFixed(1)}`).join(", ")} · rain ${game.scene.particleSystems.map((ps) => ps.getActiveCount()).join("+")} · route yaw ${game.scene.getTransformNodeByName("taxi_continuous_route")?.rotation.y.toFixed(3)} · dialogue ${document.querySelector(".story-subtitles:not([hidden])")?.textContent ?? "silent"}`;
  });
}
window.addEventListener("unhandledrejection", (e) => {
  output.textContent += `\nERROR ${String(e.reason)}`;
});
void boot().catch((error) => {
  output.textContent = `FAIL ${String(error)}`;
});
