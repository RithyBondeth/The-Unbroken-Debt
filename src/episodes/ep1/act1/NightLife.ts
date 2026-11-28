import type { Scene } from "@babylonjs/core/scene";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import type { Game } from "@/core/Game";
import type { Area } from "@/core/areaLoader";
import { seededRandom } from "@/audio/synth";
import { ep2AudioUrls } from "../audio/VillageAudio";
import "@babylonjs/core/Particles/particleSystemComponent";

/** Seconds between distant rural night calls (Cambodian village dogs, owl, Tokay gecko, bamboo creaks). */
const CALL_GAP: [number, number] = [10, 24];

interface Bat {
  node: TransformNode;
  wings: [Mesh, Mesh];
  centre: Vector3;
  radius: number;
  speed: number;
  phase: number;
}

interface WildlifeLoop {
  sound: StaticSound;
  base: number;
}

/**
 * The village's living night, redesigned with real mastered Southeast Asian CC0
 * field recordings (flooded paddy frogs, tropical night crickets, distant Cambodian
 * street dogs, Tokay gecko, scops owl, bamboo & tree creaks) — with the old unverified
 * `amb_ep1_smot` MP3 loop completely removed.
 */
export class NightLife {
  /** Ambient wildlife drops silent before major scares and Act II handover. */
  threatSilence = 0;
  private readonly loops: WildlifeLoop[] = [];
  private readonly calls: { sounds: StaticSound[]; near: Vector3[] }[] = [];
  private readonly bats: Bat[] = [];
  private time = 0;
  private nextCall = 7;
  private presenceQuiet = 0;
  private readonly rand = seededRandom(1932);

  constructor(
    private readonly game: Game,
    area: Area,
    private readonly localSilence: () => number = () => 0,
  ) {
    const scene = game.scene;
    this.makeBats(scene);
    const markers = area.level.markers;
    for (const [id, marker] of markers)
      if (id.startsWith("flies")) this.flies(scene, marker.position);
    for (const [id, flame] of area.level.flames)
      if (id.startsWith("tent_") || id === "fu_bulb") this.moths(scene, flame.position);
  }

  stopForDawn(): void {
    this.threatSilence = 1;
    for (const l of this.loops) l.sound.stop();
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const pos = (x: number, y: number, z: number) => new Vector3(-x, z, -y); // Blender to Babylon

    const addLoop = async (
      name: string,
      ep2Clip: string,
      at: Vector3,
      volume: number,
      minDistance: number,
    ) => {
      const buffer = await audio.load(ep2AudioUrls(ep2Clip));
      if (!buffer) return;
      const sound = await audio.spatialSound(name, buffer, "ambience", at, {
        loop: true,
        distanceModel: "linear",
        minDistance,
        maxDistance: 58,
        volume,
      });
      sound.play();
      this.loops.push({ sound, base: volume });
    };

    // Real Southeast Asian paddy frogs, pond water, and tropical night crickets
    // (canopy wind is owned solely by WindAudio so there are zero stacked wind beds)
    await Promise.all([
      addLoop("village_frogs_w", "amb_ep2_frogs_a", pos(-22, -24, 0), 0.28, 12),
      addLoop("village_frogs_e", "amb_ep2_frogs_b", pos(24, -22, 0), 0.26, 12),
      addLoop("village_pond_water", "amb_ep2_pond", pos(-38, 12, 0), 0.2, 8),
      addLoop("village_insects_n", "amb_ep2_insects_a", pos(-10, 26, 0.8), 0.18, 12),
      addLoop("village_insects_s", "amb_ep2_insects_b", pos(8, -42, 0.8), 0.18, 12),
    ]);

    const addCallGroup = async (
      groupName: string,
      clips: string[],
      volume: number,
      near: Vector3[],
    ) => {
      const sounds: StaticSound[] = [];
      for (const clip of clips) {
        const buffer = await audio.load(ep2AudioUrls(clip));
        if (!buffer) continue;
        sounds.push(
          await audio.spatialSound(`${groupName}_${clip}`, buffer, "ambience", near[0], {
            minDistance: 8,
            maxDistance: 85,
            volume,
          }),
        );
      }
      if (sounds.length) this.calls.push({ sounds, near });
    };

    const farDogs = [pos(-36, -42, 1), pos(34, -36, 1), pos(-30, 32, 1), pos(32, 14, 1)];
    await Promise.all([
      addCallGroup(
        "cambodian_dogs",
        ["sfx_ep2_dog_1", "sfx_ep2_dog_2", "sfx_ep2_dog_3", "sfx_ep2_dog_4"],
        0.24,
        farDogs,
      ),
      addCallGroup("scops_owl", ["sfx_ep2_owl_1", "sfx_ep2_owl_2", "sfx_ep2_owl_3"], 0.22, [
        pos(-7, -35, 9),
        pos(15, 10, 12),
        pos(-22, 16, 10),
      ]),
      addCallGroup("tokay_gecko", ["sfx_ep2_gecko_1", "sfx_ep2_gecko_2"], 0.24, [
        pos(-5, 18.8, 4.5),
        pos(5, 9.2, 4.5),
        pos(-24, 18, 4.2),
      ]),
      addCallGroup(
        "bamboo_creak",
        ["sfx_ep2_creak_bamboo_1", "sfx_ep2_creak_bamboo_2", "sfx_ep2_creak_tree_1"],
        0.28,
        [pos(-14, -26, 2.0), pos(12, -16, 2.0), pos(-18, 8, 2.0), pos(18, 6, 2.0)],
      ),
    ]);
  }

  update(dt: number): void {
    this.time += dt;
    const t = this.time;
    const quietTarget = this.game.threatActive ? 0.92 : this.localSilence() * 0.9;
    this.presenceQuiet += (quietTarget - this.presenceQuiet) * (1 - Math.exp(-dt / 0.8));
    const keep = Math.max(0, 1 - Math.max(this.threatSilence, this.presenceQuiet));
    for (const l of this.loops) l.sound.volume = l.base * keep;

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
      const group = this.calls[Math.floor(this.rand() * this.calls.length)];
      const sound = group.sounds[Math.floor(this.rand() * group.sounds.length)];
      sound.spatial.position = group.near[Math.floor(this.rand() * group.near.length)].clone();
      sound.playbackRate = 0.94 + this.rand() * 0.12;
      sound.play();
      this.nextCall = t + CALL_GAP[0] + this.rand() * (CALL_GAP[1] - CALL_GAP[0]);
    }
  }

  /** Bats circling over the courtyard and roofs. */
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
