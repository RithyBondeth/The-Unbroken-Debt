import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "@/core/Game";
import { Preay } from "../entities/Preay";
import { COFFIN } from "../data/funeral";

/**
 * Where she stands in the approved funeral previews (Nov 21, 2026): in the dark behind the
 * monks' empty table, turned to the coffin, a guttering candle at her feet
 * (funeral_under.MONKS at Blender (-1.5, 15.9); she stands at Blender (-1.9, 17.55)).
 */
const AT = new Vector3(1.9, 0, -17.55);
/** Sora this close and she is gone. */
const NEAR = 3.2;
/** Seen this long in all, then gone the next time Sora looks away for a moment. */
const SEEN_FOR = 1.6;
const AWAY_FOR = 0.5;

/**
 * The watcher at the funeral in Act I: the Preay standing still behind the monks' table,
 * her head coming round to Sora when Sora is near. Once Sora has had a look at her and
 * looked away, or walks up to her, she is not there any more, and does not come back.
 */
export class FuneralWatcher {
  private readonly figure: Preay;
  private seen = 0;
  private away = 0;
  private gone: boolean;

  constructor(
    private readonly game: Game,
    asset: AssetContainer,
    ground: (x: number, z: number) => number,
  ) {
    this.figure = new Preay(asset, "funeral_watcher", 1.7);
    this.figure.ground = ground;
    const at = new Vector3(AT.x, ground(AT.x, AT.z) - 0.02, AT.z);
    this.figure.place(at, Math.atan2(COFFIN.x - at.x, COFFIN.z - at.z));
    this.gone = game.flags.get("ep1.funeral.watcherGone", false);
    this.figure.setEnabled(!this.gone && !game.flags.get("ep1.act2.started", false));
  }

  update(dt: number, allowed: boolean): void {
    const g = this.game;
    if (this.gone) return;
    if (!allowed || g.flags.get("ep1.act2.started", false)) {
      this.figure.setEnabled(false);
      return;
    }
    this.figure.setEnabled(true);
    const eye = g.camera.globalPosition;
    const feet = g.player.feet;
    const near = Math.hypot(feet.x - AT.x, feet.z - AT.z);
    this.figure.watch(near < 9 ? eye : null);
    this.figure.standStill(dt);
    const onScreen = this.figure.figure.meshes.some((mesh) => g.camera.isInFrustum(mesh));
    if (onScreen) {
      this.seen += dt;
      this.away = 0;
    } else if (this.seen > 0) this.away += dt;
    if (near < NEAR || (this.seen >= SEEN_FOR && this.away >= AWAY_FOR)) {
      this.gone = true;
      this.figure.setEnabled(false);
      g.flags.set("ep1.funeral.watcherGone", true);
    }
  }

  dispose(): void {
    this.figure.dispose();
  }
}
