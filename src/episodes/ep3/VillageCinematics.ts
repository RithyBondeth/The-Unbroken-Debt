import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Game } from "@/core/Game";
import { CinematicDirector } from "@/shared/cinematics/CinematicDirector";
import { dialogueScript } from "@/shared/cinematics/timeline";
import { RITUAL_FIGURES } from "./data/village";

/** The same pausable, skippable, captioned cinematic runtime as the pagoda. */
export class VillageCinematics {
  readonly director: CinematicDirector;
  private readonly reduced = matchMedia("(prefers-reduced-motion: reduce)");
  constructor(private readonly game: Game) {
    this.director = new CinematicDirector(game);
  }
  async conversation(id: "seller" | "vuthy" | "lok", lines: readonly string[]): Promise<void> {
    const g = this.game,
      root = g.scene.getTransformNodeByName("npc_" + id);
    if (!root) return;
    root.rotationQuaternion = null;
    const original = g.player.feet.clone(),
      yaw = g.player.yaw,
      pitch = g.player.pitch;
    const at = root.getAbsolutePosition();
    g.player.teleport(at.add(new Vector3(0, 0.05, 1.5)), Math.PI);
    g.player.pitch = 0.04;
    g.fallGuard.reset(g.player.feet);
    const who = id === "lok" ? "Pa Lok" : id === "vuthy" ? "Vuthy" : "Noodle seller";
    try {
      await this.director.play(
        dialogueScript(
          "ep3." + id,
          who,
          lines.map((text) => [who, text]),
        ),
        ({ elapsed, reducedMotion }) => {
          if (!reducedMotion) root.rotation.z = Math.sin(elapsed * 0.9) * 0.009;
          this.pose(root, "left", reducedMotion ? 0 : Math.sin(elapsed * 0.7) ** 2 * 0.12);
        },
      );
    } finally {
      root.rotation.z = 0;
      this.pose(root, "left", 0);
      g.player.teleport(original, yaw);
      g.player.pitch = pitch;
      g.fallGuard.reset(original);
    }
  }
  async release(kanha: TransformNode, pich: TransformNode, free: boolean): Promise<void> {
    const g = this.game,
      at = g.player.feet.clone(),
      yaw = g.player.yaw,
      pitch = g.player.pitch;
    kanha.setEnabled(true);
    pich.setEnabled(true);
    const mother = Vector3.FromArray(RITUAL_FIGURES.mother),
      child = Vector3.FromArray(RITUAL_FIGURES.child);
    const faceYaw = Math.atan2(mother.x - at.x, mother.z - at.z),
      facePitch = Math.atan2(
        at.y + 1.58 - (mother.y + 1.5),
        Math.hypot(mother.x - at.x, mother.z - at.z),
      );
    g.player.yaw = faceYaw;
    g.player.pitch = facePitch;
    try {
      await this.director.play(
        dialogueScript(
          "ep3.release",
          free ? "Kanha and Pich" : "The third seal",
          free
            ? [
                ["Sora", "Kanha. I know your name. Pich, take your mother’s hand."],
                ["Sora", "The water has held you long enough. You can go now."],
              ]
            : [["Sora", "The seal is broken. I have to go."]],
        ),
        ({ progress, reducedMotion }) => {
          kanha.setAbsolutePosition(mother.add(new Vector3(progress * 0.12, 0, 0)));
          pich.setAbsolutePosition(child.add(new Vector3(-progress * 0.1, 0, 0)));
          this.pose(kanha, "right", free ? Math.sin(progress * Math.PI) * 0.6 : 0.1);
          for (const mesh of [...kanha.getChildMeshes(), ...pich.getChildMeshes()])
            mesh.visibility = 1 - Math.max(0, (progress - 0.6) / 0.4);
          if (!reducedMotion) {
            g.player.yaw = faceYaw + Math.sin(progress * Math.PI) * 0.08;
            g.player.pitch = facePitch - 0.08 * Math.sin(progress * Math.PI);
          }
        },
      );
    } finally {
      for (const root of [kanha, pich]) {
        root.setEnabled(false);
        for (const mesh of root.getChildMeshes()) mesh.visibility = 1;
      }
      g.player.teleport(at, yaw);
      g.player.pitch = pitch;
    }
  }
  updateAmbient(seconds: number): void {
    for (const name of [
      "npc_seller",
      "npc_lok",
      "npc_vuthy",
      "market_resident_0",
      "market_resident_1",
      "market_resident_2",
      "market_resident_3",
      "kanha",
      "pich",
    ]) {
      const root = this.game.scene.getTransformNodeByName(name);
      if (!root || this.director.active) continue;
      const blinkPhase = (seconds + root.uniqueId * 0.27) % 6.4;
      this.pose(
        root,
        "blink",
        blinkPhase < 0.18 ? Math.sin((Math.PI * blinkPhase) / 0.18) ** 2 : 0,
      );
      this.pose(
        root,
        "right",
        this.reduced.matches ? 0 : (0.5 + 0.5 * Math.sin(seconds * 0.5 + root.uniqueId)) * 0.045,
      );
    }
  }
  private pose(root: TransformNode, name: string, value: number): void {
    for (const mesh of root.getChildMeshes())
      if (mesh instanceof Mesh) {
        const manager = mesh.morphTargetManager;
        if (manager)
          for (let i = 0; i < manager.numTargets; i++) {
            const target = manager.getTarget(i);
            if (target.name === name) target.influence = value;
          }
      }
  }
}
