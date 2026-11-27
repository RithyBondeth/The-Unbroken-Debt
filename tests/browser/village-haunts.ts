/**
 * Isolated dev-only gallery harness for Episode 1 Village's redesigned haunted scenes.
 * Open `/tests/browser/village-haunts.html?auto` to render and save all 10 high-res WebGPU
 * screenshots cleanly into `debug-shots/`, or without `?auto` to inspect interactively.
 */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "@/core/Game";
import { createEngine } from "@/render/createEngine";
import { detectDevice } from "@/render/detectDevice";
import { useLocalDecoders } from "@/render/decoders";
import { SaveStore } from "@/systems/saves/SaveStore";
import { saveShot } from "@/debug/saveShot";
import type { ActOne } from "@/episodes/ep1/act1/ActOne";

interface ShotSpec {
  id: string;
  label: string;
  feet: [number, number, number];
  lookAt: [number, number, number];
  exactY?: boolean;
  lamp: boolean;
  flash?: boolean;
  coldAura?: number;
  setup: (act: ActOne, eye: Vector3) => void;
}

const SHOTS: readonly ShotSpec[] = [
  {
    id: "haunt-01-roadside-peeker",
    label: "1. Roadside Preay Corner-Peeker",
    feet: [-6.8, 0.1, 52.2],
    lookAt: [-9.4, 1.32, 49.4],
    lamp: true,
    flash: true,
    setup: (act, eye) => {
      act.krasue.model.root.setEnabled(false);
      act.horror.stagePreview("roadsidePeeker", eye);
    },
  },
  {
    id: "haunt-02-barber-headless",
    label: "2. Barber Shop Headless Ghost (Full Body)",
    feet: [11.9, 0.1, 49.4],
    lookAt: [11.7, 1.24, 44.1],
    lamp: true,
    flash: true,
    setup: (act, eye) => {
      act.krasue.model.root.setEnabled(false);
      act.horror.stagePreview("barberHeadless", eye);
    },
  },
  {
    id: "haunt-03-krasue-paddies-green",
    label: "3. Rice-Field Krasue (Emerald-Green)",
    feet: [8.8, 0.05, 30.2],
    lookAt: [17.2, 2.2, 27.6],
    lamp: false,
    setup: (act, eye) => {
      act.horror.stagePreview("clear", eye);
      const pos = new Vector3(17.2, 2.5, 27.6);
      act.krasue.model.root.setEnabled(true);
      act.krasue.model.redness = 0.0;
      act.krasue.model.pose(pos, eye, 1.2, false, new Vector3(-0.7, 0, -0.7), false, -1);
    },
  },
  {
    id: "haunt-04-krasue-paddies-red",
    label: "4. Rice-Field Krasue (Blood-Red Hunting)",
    feet: [8.8, 0.05, 30.2],
    lookAt: [14.5, 2.25, 28.4],
    lamp: true,
    setup: (act, eye) => {
      act.horror.stagePreview("clear", eye);
      const pos = new Vector3(14.5, 2.45, 28.4);
      act.krasue.model.root.setEnabled(true);
      act.krasue.model.redness = 1.0;
      act.krasue.model.pose(pos, eye, 2.4, true, eye.subtract(pos).normalize(), true, 0.48);
    },
  },
  {
    id: "haunt-05-shrouded-corpse",
    label: "5. Shrouded Corpse Inside the Forest",
    feet: [34.2, 0.0, -44.6],
    lookAt: [35.4, 0.35, -47.6],
    lamp: true,
    setup: (act, eye) => {
      act.krasue.model.root.setEnabled(false);
      act.horror.stagePreview("corpse", eye);
    },
  },
  {
    id: "haunt-06-well-headless",
    label: "6. Brick Village Well Headless Ghost (Full Body)",
    feet: [-7.9, 0.0, 33.9],
    lookAt: [-9.95, 1.08, 32.0],
    lamp: true,
    flash: true,
    setup: (act, eye) => {
      act.krasue.model.root.setEnabled(false);
      act.horror.stagePreview("wellHeadless", eye);
    },
  },
  {
    id: "haunt-07-preay-weeping-twist",
    label: "7. Weeping Preay · 110° Neck Twist",
    feet: [22.2, 0.0, -23.5],
    lookAt: [24.5, 1.38, -26.2],
    lamp: true,
    flash: true,
    coldAura: 0.65,
    setup: (act, eye) => {
      act.krasue.model.root.setEnabled(false);
      act.horror.stagePreview("weepingTwist", eye);
    },
  },
  {
    id: "haunt-08-preay-strobe-closer",
    label: "8. Preay Lightning Strobe-Closer",
    feet: [0.0, 0.0, 22.8],
    lookAt: [0.35, 1.32, 18.2],
    lamp: true,
    flash: true,
    coldAura: 0.8,
    setup: (act, eye) => {
      act.krasue.model.root.setEnabled(false);
      act.horror.stagePreview("strobeCloser", eye);
    },
  },
  {
    id: "haunt-09-shadow-banner",
    label: "9. Funeral-Banner Shadow Silhouette",
    feet: [0.6, 0.0, -14.2],
    lookAt: [-2.8, 1.32, -20.4],
    lamp: true,
    flash: true,
    setup: (act, eye) => {
      act.krasue.model.root.setEnabled(false);
      act.horror.stagePreview("shadowBanner", eye);
    },
  },
  {
    id: "haunt-10-preay-provoked-ambush",
    label: "10. Provoked Preay & 20:12 Watch Glitch",
    feet: [-0.8, 2.5, -13.0],
    lookAt: [-1.8, 3.85, -15.6],
    lamp: true,
    flash: true,
    coldAura: 1.0,
    setup: (act, eye) => {
      act.krasue.model.root.setEnabled(false);
      act.horror.stagePreview("provokedAmbush", eye);
      act.clock.glitch(12);
      act.clock.glanceWatch();
    },
  },
];

const status = document.getElementById("status")!;
const nav = document.getElementById("controls")!;
const pause = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function run(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search);
  params.set("start", "act1");
  history.replaceState(null, "", `${location.pathname}?${params}`);

  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();

  const device = await detectDevice();
  const game = new Game(engine, device);
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-haunt-gallery"),
  });
  for (const flag of ["ep1.arrival.road", "ep1.arrival.courtyard", "ep1.puzzle.gate.open"]) {
    game.flags.set(flag, true);
  }
  game.fade.waitForEnter = async () => {};

  status.textContent = "Loading Episode 1 Village & Ghost Models…";
  await game.start({ audio: false });
  const act = (window as unknown as { act: ActOne }).act;
  while (game.cutscene) await pause(80);
  // Pause autonomous loops so our staged poses remain exact during frame capture
  game.cutscene = true;

  const frames = async (n = 4) => {
    for (let i = 0; i < n; i++) {
      await new Promise<void>((done) => game.scene.onAfterRenderObservable.addOnce(() => done()));
    }
  };

  let activeShot: ShotSpec | null = null;
  game.scene.onBeforeRenderObservable.add(() => {
    if (!activeShot) return;
    if (activeShot.coldAura !== undefined) act.lights.coldAura = activeShot.coldAura;
    if (activeShot.id.startsWith("haunt-03") || activeShot.id.startsWith("haunt-04")) {
      const isRed = activeShot.id.startsWith("haunt-04");
      const pos = isRed ? new Vector3(14.5, 2.45, 28.4) : new Vector3(17.2, 2.5, 27.6);
      const eye = game.camera.globalPosition;
      act.krasue.model.root.setEnabled(true);
      act.krasue.model.redness = isRed ? 1.0 : 0.0;
      act.krasue.model.pose(
        pos,
        eye,
        isRed ? 2.4 : 1.2,
        isRed,
        isRed ? eye.subtract(pos).normalize() : new Vector3(-0.7, 0, -0.7),
        isRed,
        isRed ? 0.48 : -1,
      );
    }
  });

  const PUZZLE_SHOTS: readonly ShotSpec[] = [
    {
      id: "puzzle-01-noodle-calendar",
      label: "P1. Noodle Calendar (7)",
      feet: [-1.25, 0.72, 56.95],
      lookAt: [-1.92, 1.62, 57.56],
      exactY: true,
      lamp: true,
      setup: (act, eye) => {
        act.krasue.model.root.setEnabled(false);
        act.horror.stagePreview("clear", eye);
      },
    },
    {
      id: "puzzle-02-moto-workbench",
      label: "P2. Moto Ledger & Crowbar",
      feet: [12.65, 0.47, 59.65],
      lookAt: [12.55, 1.05, 60.85],
      exactY: true,
      lamp: true,
      setup: (act, eye) => {
        act.krasue.model.root.setEnabled(false);
        act.horror.stagePreview("clear", eye);
      },
    },
    {
      id: "puzzle-03-gate-padlock",
      label: "P3. Gate Brass Padlock",
      feet: [0.15, 0.02, 41.65],
      lookAt: [0.22, 1.38, 40.0],
      lamp: true,
      setup: (act, eye) => {
        act.krasue.model.root.setEnabled(false);
        act.horror.stagePreview("clear", eye);
        game.scene.getTransformNodeByName("interact_village_gate_lock")?.setEnabled(true);
      },
    },
    {
      id: "puzzle-04-hall-clock",
      label: "P4. Hall 20:12 Pendulum Clock",
      feet: [-4.45, 2.5, -13.5],
      lookAt: [-3.09, 4.12, -13.5],
      exactY: true,
      lamp: true,
      setup: (act, eye) => {
        act.krasue.model.root.setEnabled(false);
        act.horror.stagePreview("clear", eye);
        game.flags.set("ep1.puzzle.clock.pendulumFitted", true);
      },
    },
  ];

  const stage = async (spec: ShotSpec) => {
    activeShot = spec;
    const fy =
      spec.exactY || spec.feet[1] > 1.5
        ? spec.feet[1]
        : act.border.groundAt(spec.feet[0], spec.feet[2]);
    const feet = new Vector3(spec.feet[0], fy, spec.feet[2]);
    const eye = new Vector3(feet.x, feet.y + 1.58, feet.z);
    const target = new Vector3(...spec.lookAt);
    const d = target.subtract(eye);
    const yaw = Math.atan2(d.x, d.z);
    const pitch = Math.atan2(-d.y, Math.hypot(d.x, d.z));

    game.stopInspecting();
    game.player.teleport(feet, yaw);
    game.player.pitch = pitch;
    act.lights.coldAura = spec.coldAura ?? 0;
    if (spec.lamp) act.vigil.lamp.light();
    else if (act.vigil.lamp.burning) act.vigil.lamp.putOut();

    await frames(3);
    spec.setup(act, game.camera.globalPosition);
    if (spec.flash) act.lights.storm.strike();
    await frames(5);
    const openFloors = [0, 2, 3, 5, 6, 7].filter(
      (i) => game.scene.getTransformNodeByName(`col_vroad_shop_${i}_open_floor`) !== null,
    ).length;
    const oldBarberBlocked = Boolean(
      game.scene.getTransformNodeByName("col_vroad_shop_5_in_body")?.physicsBody,
    );
    status.textContent = `Staged: ${spec.label} | OpenShops=${openFloors}/6 OldBarberBlocked=${oldBarberBlocked}`;
  };

  for (const spec of [...SHOTS, ...PUZZLE_SHOTS]) {
    const btn = document.createElement("button");
    btn.textContent = spec.label;
    btn.onclick = () => void stage(spec);
    nav.append(btn);
  }

  const captureList = async (list: readonly ShotSpec[], label: string) => {
    document.body.classList.add("capturing");
    engine.setSize(1280, 720);
    await frames(2);
    for (const spec of list) {
      await stage(spec);
      if (spec.flash) act.lights.storm.strike();
      await frames(2);
      await saveShot(engine, game.camera, spec.id);
    }
    engine.resize();
    document.body.classList.remove("capturing");
    status.textContent = `DONE: Captured ${list.length} ${label} screenshots into debug-shots/`;
  };

  const capBtn = document.createElement("button");
  capBtn.textContent = "Capture All 10";
  capBtn.onclick = () => void captureList(SHOTS, "haunt");
  nav.append(capBtn);

  const capPuzBtn = document.createElement("button");
  capPuzBtn.textContent = "Capture Puzzles";
  capPuzBtn.onclick = () => void captureList(PUZZLE_SHOTS, "puzzle");
  nav.append(capPuzBtn);

  const lockUiBtn = document.createElement("button");
  lockUiBtn.textContent = "Preview Padlock UI";
  lockUiBtn.onclick = () => {
    game.flags.set("ep1.clue.noodleCalendar", true);
    game.flags.set("ep1.clue.motoLedger", true);
    game.cutscene = false;
    game.bus.emit("interact:use", { id: "interact_village_gate_lock" });
  };
  nav.append(lockUiBtn);

  if (params.has("auto")) {
    await captureList(SHOTS, "haunt");
  } else if (params.has("puzzles")) {
    await captureList(PUZZLE_SHOTS, "puzzle");
  } else {
    await stage(SHOTS[0]);
  }
}

void run().catch((err: unknown) => {
  status.textContent = `FAIL ${String(err)}`;
  console.error(err);
});
