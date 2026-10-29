import type { Scene } from "@babylonjs/core/scene";
import type { AbstractSound } from "@babylonjs/core/AudioV2/abstractAudio/abstractSound";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import type { Game } from "../../../core/Game";
import type { Area } from "../../../core/AreaLoader";
import { seededRandom } from "../../../audio/synth";
import {
  chantDrone,
  cricketsLoop,
  crowCaws,
  dogBarks,
  dogHowl,
  frogsLoop,
  geckoCall,
  owlHoot,
  branchSnap,
} from "../audio/nightSounds";
import "@babylonjs/core/Particles/particleSystemComponent";

/**
 * The funeral recitation (smot) from the pavilion, streamed: Opus first, AAC for
 * browsers without it (Audio Design Document 10). Made from the recording in
 * art-source/audio/ep1 (Cultural Guide: real chanting only with permission).
 * Without the files the pavilion plays a wordless placeholder drone.
 */
export const SMOT_URLS = ["assets/ep1/audio/amb_ep1_smot.ogg", "assets/ep1/audio/amb_ep1_smot.m4a"];

/** Seconds between the distant calls: a dog, the owl, crows, the gecko. */
const CALL_GAP: [number, number] = [9, 22];

const asset = (path: string) => `${import.meta.env.BASE_URL}${path}`;

interface Bat {
  node: TransformNode;
  wings: [Mesh, Mesh];
  centre: Vector3;
  radius: number;
  speed: number;
  phase: number;
}

/**
 * The village's night (Audio Design Document, section 4): frogs in the flooded
 * fields, crickets everywhere, calls from far off (dogs, an owl, crows, a gecko
 * under the eaves), the funeral recitation from the pavilion; bats over the
 * yard, moths round the tent's lanterns, flies over the offerings.
 */
export class NightLife {
  /** The insects fall quiet before A2-01; ceremonial chanting is left alone. */
  threatSilence = 0;
  private readonly loops: StaticSound[] = [];
  private readonly calls: { sound: StaticSound; near: Vector3[] }[] = [];
  stopForDawn(): void {
    this.threatSilence = 1;
    this.chant?.stop();
    this.loops.forEach((sound) => sound.stop());
  }

  private chant: AbstractSound | null = null;
  private readonly bats: Bat[] = [];
  private time = 0;
  private nextCall = 6;
  private presenceQuiet = 0;
  private readonly rand = seededRandom(1932);

  constructor(
    private readonly game: Game,
    private readonly area: Area,
    private readonly localSilence: () => number = () => 0,
  ) {
    const scene = game.scene;
    this.makeBats(scene);
    const markers = area.level.markers;
    for (const [id, marker] of markers)
      if (id.startsWith("flies")) this.flies(scene, marker.position);
    for (const [id, flame] of area.level.flames)
      if (id.startsWith("tent_")) this.moths(scene, flame.position);
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const pos = (x: number, y: number, z: number) => new Vector3(-x, z, -y); // Blender to Babylon
    const loop = async (
      name: string,
      samples: Float32Array,
      at: Vector3,
      volume: number,
      minDistance: number,
    ) => {
      const sound = await audio.spatialSound(name, audio.buffer(samples, rate), "ambience", at, {
        loop: true,
        minDistance,
        volume,
      });
      sound.play();
      this.loops.push(sound);
    };
    // Frogs across the flooded fields south of the road, and in the pond: a bed
    // well under the recitation.
    await loop("frogs_w", frogsLoop(rate, seededRandom(41)), pos(-20, -72, 0), 0.35, 10);
    await loop("frogs_e", frogsLoop(rate, seededRandom(42)), pos(20, -75, 0), 0.35, 10);
    await loop("frogs_pond", frogsLoop(rate, seededRandom(43)), pos(-20, 19, 0), 0.2, 5);
    await loop("crickets_n", cricketsLoop(rate, seededRandom(44)), pos(-10, 10, 0.5), 0.2, 10);
    await loop("crickets_s", cricketsLoop(rate, seededRandom(45)), pos(8, -30, 0.5), 0.2, 10);
    // Each call's volume brings it to about -28 LUFS at its near distance (the
    // synthesised calls differ by 10 dB as made: the howl and the owl run hot).
    const call = async (name: string, samples: Float32Array, volume: number, near: Vector3[]) => {
      const sound = await audio.spatialSound(
        name,
        audio.buffer(samples, rate),
        "ambience",
        near[0],
        { minDistance: 8, maxDistance: 80, volume },
      );
      this.calls.push({ sound, near });
    };
    const far = [pos(-34, 2, 1), pos(32, 14, 1), pos(-26, 30, 1), pos(28, -24, 1)];
    await call("dog_howl", dogHowl(rate, seededRandom(46)), 0.16, far);
    await call("dog_barks", dogBarks(rate, seededRandom(47)), 0.31, far);
    await call("owl", owlHoot(rate, seededRandom(48)), 0.18, [
      pos(-7, -35, 9),
      pos(15, 10, 12),
      pos(-20, 14, 10),
    ]);
    await call("crows", crowCaws(rate, seededRandom(49)), 0.29, [
      pos(-5, -15, 8),
      pos(6, -24, 8),
      pos(-14, -48, 8),
    ]);
    await call("gecko", geckoCall(rate, seededRandom(50)), 0.25, [
      pos(-5, 18.8, 4.5),
      pos(5, 9.2, 4.5),
    ]);
    // Something moving out in the trees: a dead branch snapping, never where you look.
    await call("branch", branchSnap(rate, seededRandom(52)), 0.6, [
      pos(-12, -30, 0.2),
      pos(10, -18, 0.2),
      pos(-18, 6, 0.2),
      pos(16, 2, 0.2),
    ]);
    // The recitation from the pavilion, the whole night through: the real smot if
    // supplied, else the placeholder. Full within the courtyard, still there at the
    // gate, faint from the road (about -34 LUFS at 50 m).
    const tent = this.area.level.flames.get("altar_0")?.position.clone() ?? pos(0, 4, 1);
    const options = { loop: true, minDistance: 10, maxDistance: 120 };
    this.chant = (await this.hasSmot())
      ? await audio.spatialStream("smot", SMOT_URLS.map(asset), "ambience", tent, {
          ...options,
          volume: 1,
        })
      : await audio.spatialSound(
          "smot",
          audio.buffer(chantDrone(rate, seededRandom(51)), rate),
          "ambience",
          tent,
          { ...options, volume: 0.35 },
        );
    this.chant.play();
  }

  /** Whether the recording is there (the dev server answers a missing file with the page). */
  private async hasSmot(): Promise<boolean> {
    try {
      const response = await fetch(asset(SMOT_URLS[0]), { method: "HEAD" });
      return response.ok && (response.headers.get("content-type") ?? "").startsWith("audio");
    } catch {
      return false;
    }
  }

  update(dt: number): void {
    this.time += dt;
    const t = this.time;
    const volumes = [0.35, 0.35, 0.2, 0.2, 0.2];
    this.presenceQuiet +=
      ((this.game.threatActive ? 0.88 : this.localSilence() * 0.85) - this.presenceQuiet) *
      (1 - Math.exp(-dt / 1.2));
    this.loops.forEach(
      (sound, i) =>
        (sound.volume = volumes[i] * (1 - Math.max(this.threatSilence, this.presenceQuiet))),
    );
    for (const bat of this.bats) {
      const a = t * bat.speed + bat.phase;
      bat.node.position.set(
        bat.centre.x + Math.cos(a) * bat.radius + Math.sin(a * 2.7) * 1.5,
        bat.centre.y + Math.sin(a * 1.9) * 1.2,
        bat.centre.z + Math.sin(a) * bat.radius * 0.7 + Math.cos(a * 3.1) * 1.2,
      );
      bat.node.rotation.y = -a + Math.PI / 2;
      const flap = Math.sin(t * 22 + bat.phase) * 0.9;
      bat.wings[0].rotation.z = flap;
      bat.wings[1].rotation.z = -flap;
    }
    if (
      this.threatSilence === 0 &&
      !this.game.threatActive &&
      this.localSilence() < 0.1 &&
      t >= this.nextCall &&
      this.calls.length
    ) {
      const call = this.calls[Math.floor(this.rand() * this.calls.length)];
      call.sound.spatial.position = call.near[Math.floor(this.rand() * call.near.length)].clone();
      call.sound.play();
      this.nextCall = t + CALL_GAP[0] + this.rand() * (CALL_GAP[1] - CALL_GAP[0]);
    }
  }

  /** Bats circling over the courtyard and the pavilion's light. */
  private makeBats(scene: Scene): void {
    const skin = new StandardMaterial("M_bat", scene);
    skin.diffuseColor = new Color3(0.04, 0.035, 0.03);
    skin.specularColor = Color3.Black();
    skin.backFaceCulling = false;
    const wingShape = (side: number): Mesh => {
      const wing = new Mesh(`bat_wing_${side}`, scene);
      const data = new VertexData();
      data.positions = [
        0,
        0,
        -0.05,
        0,
        0,
        0.06,
        side * 0.22,
        0.02,
        0.03,
        side * 0.3,
        0,
        -0.06,
        side * 0.14,
        0.01,
        -0.07,
      ];
      data.indices = [0, 1, 2, 0, 2, 3, 0, 3, 4];
      data.normals = [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0];
      data.applyToMesh(wing);
      wing.material = skin;
      return wing;
    };
    for (let k = 0; k < 7; k++) {
      const node = new TransformNode(`bat_${k}`, scene);
      const body = new Mesh(`bat_body_${k}`, scene);
      const data = new VertexData();
      data.positions = [0, 0.02, 0.07, -0.025, 0, 0, 0.025, 0, 0, 0, -0.01, -0.07, 0, 0.025, 0];
      data.indices = [0, 1, 4, 0, 4, 2, 1, 3, 4, 4, 3, 2, 0, 2, 1, 1, 2, 3];
      VertexData.ComputeNormals(data.positions, data.indices, (data.normals = []));
      data.applyToMesh(body);
      body.material = skin;
      body.parent = node;
      const wings: [Mesh, Mesh] = [wingShape(1), wingShape(-1)];
      for (const w of wings) w.parent = node;
      for (const m of [body, ...wings]) m.isPickable = false;
      this.bats.push({
        node,
        wings,
        centre: new Vector3((this.rand() - 0.5) * 16, 6 + this.rand() * 6, -(this.rand() * 20 - 4)),
        radius: 3 + this.rand() * 6,
        speed: 0.5 + this.rand() * 0.6,
        phase: this.rand() * 10,
      });
    }
  }

  /** Moths blundering round a lantern. */
  private moths(scene: Scene, at: Vector3): void {
    const ps = new ParticleSystem("moths", 12, scene);
    ps.particleTexture = speck(scene, "T_moth", "rgba(230,215,190,1)");
    ps.emitter = at.clone();
    ps.minEmitBox.set(-0.3, -0.2, -0.3);
    ps.maxEmitBox.set(0.3, 0.3, 0.3);
    ps.direction1 = new Vector3(-0.6, -0.3, -0.6);
    ps.direction2 = new Vector3(0.6, 0.5, 0.6);
    ps.minEmitPower = 0.2;
    ps.maxEmitPower = 0.6;
    ps.minLifeTime = 1.5;
    ps.maxLifeTime = 3;
    ps.minSize = 0.015;
    ps.maxSize = 0.025;
    ps.emitRate = 5;
    ps.color1 = new Color4(1, 0.95, 0.85, 1);
    ps.color2 = new Color4(0.9, 0.85, 0.75, 1);
    ps.colorDead = new Color4(0.9, 0.85, 0.75, 0);
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    ps.preWarmCycles = 60;
    ps.start();
  }

  /** Flies buzzing over rotting offerings. */
  private flies(scene: Scene, at: Vector3): void {
    const ps = new ParticleSystem("flies", 30, scene);
    ps.particleTexture = speck(scene, "T_fly", "rgba(20,18,16,1)");
    ps.emitter = at.clone();
    ps.minEmitBox.set(-0.2, 0, -0.2);
    ps.maxEmitBox.set(0.2, 0.25, 0.2);
    ps.direction1 = new Vector3(-1, -0.5, -1);
    ps.direction2 = new Vector3(1, 0.8, 1);
    ps.minEmitPower = 0.3;
    ps.maxEmitPower = 0.9;
    ps.minLifeTime = 0.4;
    ps.maxLifeTime = 0.9;
    ps.minSize = 0.008;
    ps.maxSize = 0.012;
    ps.emitRate = 35;
    ps.color1 = new Color4(0.1, 0.09, 0.08, 1);
    ps.color2 = new Color4(0.05, 0.05, 0.04, 1);
    ps.colorDead = new Color4(0.05, 0.05, 0.04, 0);
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    ps.start();
  }
}

/** A small soft dot for insects. */
function speck(scene: Scene, name: string, colour: string): DynamicTexture {
  const texture = new DynamicTexture(name, { width: 16, height: 16 }, scene, false);
  const ctx = texture.getContext();
  ctx.clearRect(0, 0, 16, 16);
  ctx.fillStyle = colour;
  ctx.beginPath();
  ctx.arc(8, 8, 6, 0, Math.PI * 2);
  ctx.fill();
  texture.hasAlpha = true;
  texture.update();
  return texture;
}
