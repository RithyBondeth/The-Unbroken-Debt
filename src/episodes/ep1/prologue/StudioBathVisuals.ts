import { FreeCamera } from "@babylonjs/core/Cameras/freeCamera";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { RenderTargetTexture } from "@babylonjs/core/Materials/Textures/renderTargetTexture";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Scene } from "@babylonjs/core/scene";
import { seededRandom } from "@/audio/synth";
import { runtime } from "../data/studioScares";

interface RippleRing {
  mesh: Mesh;
  age: number;
  delay: number;
  active: boolean;
}

/**
 * Photorealistic runtime visual effects for the 1932 Phnom Penh bathroom:
 * - Clean, tarnished live 3D `RenderTargetTexture` reflection in the antique mirror
 *   synced to the flickering Edison pendant bulb (zero 2D cartoon cracks or painted arms).
 * - Running cold tap water, expanding dark cistern ripples, and progressive wet bare
 *   footprints trailing out of the bathroom into the bedroom and hallway.
 */
export class StudioBathVisuals {
  readonly mirrorSteam: Mesh;
  private readonly mirrorTex: RenderTargetTexture | null = null;
  private readonly mirrorCam: FreeCamera | null = null;
  private readonly mirrorMat: StandardMaterial | null = null;
  private readonly mirrorRoomFill: PointLight | null = null;
  private readonly mirrorAt: Vector3;
  private readonly faucetStream: Mesh;
  private readonly faucetSplash: Mesh;
  private readonly faucetMat: PBRMaterial;
  private readonly ripples: RippleRing[] = [];
  private readonly footprints: Mesh[] = [];
  private mirrorLightGain = 1;
  private mirrorActive = false;
  private mirrorFastRefresh = false;
  private faucetRunning = false;
  private footprintRevealT = -1;
  private clock = 0;

  constructor(
    private readonly scene: Scene,
    anchors: {
      mirrorAt: Vector3;
      faucetAt: Vector3;
      tankAt: Vector3;
    },
  ) {
    this.mirrorAt = anchors.mirrorAt.clone();

    // 0. Live 3D reflection on the antique bathroom mirror (`bath_mirror_glass`).
    //    Only sees normal visible room geometry (never any ghost model!) and refreshes
    //    only while Sora is inside the bathroom.
    const mirrorGlass = scene.getMeshByName("bath_mirror_glass");
    if (mirrorGlass) {
      const camPos = new Vector3(this.mirrorAt.x, this.mirrorAt.y, this.mirrorAt.z + 0.03);
      const cam = new FreeCamera("bath_mirror_eye", camPos, scene);
      cam.setTarget(new Vector3(this.mirrorAt.x, this.mirrorAt.y - 0.05, this.mirrorAt.z + 2.2));
      cam.fov = 0.82;
      cam.minZ = 0.05;
      cam.maxZ = 14;
      cam.inputs.clear();
      cam.layerMask = 0x0fffffff;
      this.mirrorCam = cam;

      const rtt = new RenderTargetTexture(
        "bath_mirror_rtt",
        { width: 384, height: 480 },
        scene,
        false,
      );
      rtt.activeCamera = cam;
      rtt.clearColor = new Color4(0.015, 0.02, 0.02, 1);
      rtt.noPrePassRenderer = true;
      rtt.renderParticles = false;
      rtt.refreshRate = RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
      rtt.uScale = -1;
      rtt.uOffset = 1;
      rtt.vScale = -1;
      rtt.vOffset = 1;
      rtt.level = 1.3;
      scene.customRenderTargets.push(rtt);
      this.mirrorTex = rtt;

      // Subtle mirror-pass fill synced to the real Edison bulb so the reflected room
      // stays legible in the tarnished silvering and flickers authentically with the bulb.
      const roomFill = new PointLight(
        "bath_mirror_room_fill",
        new Vector3(this.mirrorAt.x, 2.05, this.mirrorAt.z + 1.35),
        scene,
      );
      roomFill.diffuse.set(0.74, 0.8, 0.76);
      roomFill.specular.set(0.06, 0.07, 0.06);
      roomFill.intensity = 0;
      roomFill.range = 4.6;
      roomFill.shadowEnabled = false;
      this.mirrorRoomFill = roomFill;

      rtt.onBeforeRenderObservable.add(() => {
        roomFill.intensity = 1.35 * this.mirrorLightGain;
      });
      rtt.onAfterRenderObservable.add(() => {
        roomFill.intensity = 0;
      });

      const mat = new StandardMaterial("M_bath_live_mirror", scene);
      mat.diffuseTexture = rtt;
      mat.emissiveColor.set(0.64, 0.7, 0.67);
      mat.specularColor = Color3.Black();
      mat.disableLighting = true;
      mat.backFaceCulling = false;
      mirrorGlass.material = mat;
      this.mirrorMat = mat;

      this.populateMirrorRenderList(mirrorGlass);
    }

    // 1. Subtle antique tarnished silvering & monsoon humidity veil over the live reflection
    this.mirrorSteam = CreatePlane("bath_mirror_steam", { width: 0.53, height: 0.69 }, scene);
    this.mirrorSteam.position.set(
      anchors.mirrorAt.x,
      anchors.mirrorAt.y,
      anchors.mirrorAt.z + 0.0025,
    );
    this.mirrorSteam.rotation.y = Math.PI;
    this.mirrorSteam.material = this.makeMirrorPatinaMaterial();
    this.mirrorSteam.isPickable = false;

    // 2. Running cold water stream from left brass faucet into porcelain basin
    this.faucetMat = new PBRMaterial("M_bath_faucet_stream", scene);
    this.faucetMat.albedoColor = new Color3(0.76, 0.84, 0.86);
    this.faucetMat.emissiveColor = new Color3(0.06, 0.08, 0.09);
    this.faucetMat.metallic = 0;
    this.faucetMat.roughness = 0.06;
    this.faucetMat.alpha = 0.44;
    this.faucetMat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    this.faucetMat.disableDepthWrite = true;

    const streamLen = 0.175;
    this.faucetStream = CreateCylinder(
      "bath_faucet_stream",
      { diameterTop: 0.0065, diameterBottom: 0.0095, height: streamLen, tessellation: 10 },
      scene,
    );
    this.faucetStream.position.set(
      anchors.faucetAt.x,
      anchors.faucetAt.y - streamLen / 2,
      anchors.faucetAt.z,
    );
    this.faucetStream.material = this.faucetMat;
    this.faucetStream.isPickable = false;
    this.faucetStream.isVisible = false;

    this.faucetSplash = CreatePlane("bath_faucet_splash", { size: 0.055 }, scene);
    this.faucetSplash.position.set(
      anchors.faucetAt.x,
      anchors.faucetAt.y - streamLen + 0.005,
      anchors.faucetAt.z,
    );
    this.faucetSplash.rotation.x = Math.PI / 2;
    this.faucetSplash.material = this.makeRippleMaterial("M_bath_faucet_splash", 0.36);
    this.faucetSplash.isPickable = false;
    this.faucetSplash.isVisible = false;

    // 3. Concentric ripples on the dark tiled water cistern (1 shared material + mesh.visibility)
    const sharedRippleMat = this.makeRippleMaterial("M_bath_tank_ripple", 1);
    for (let i = 0; i < 3; i++) {
      const mesh = CreatePlane(`bath_tank_ripple_${i}`, { size: 0.68 }, scene);
      mesh.position.set(anchors.tankAt.x, anchors.tankAt.y + 0.003 + i * 0.0004, anchors.tankAt.z);
      mesh.rotation.x = Math.PI / 2;
      mesh.material = sharedRippleMat;
      mesh.isPickable = false;
      mesh.isVisible = false;
      mesh.visibility = 0;
      this.ripples.push({ mesh, age: 0, delay: i * 0.48, active: false });
    }

    // 4. Wet bare footprints leading from the bathroom doorway out into the bedroom & hall
    this.buildFootprints();
  }

  /** Enables live mirror rendering only while Sora is inside the bathroom (zero cost outside). */
  setMirrorActive(active: boolean, fastRefresh = false, eye?: Vector3, power = 1): void {
    this.mirrorActive = active;
    this.mirrorFastRefresh = fastRefresh;
    if (!this.mirrorTex || !this.mirrorCam) return;
    if (!active) {
      this.mirrorTex.refreshRate = RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
      return;
    }
    this.mirrorTex.refreshRate = fastRefresh ? 1 : 2;
    this.mirrorLightGain = Math.max(0.04, Math.min(1.25, power));
    if (this.mirrorMat) {
      const gain = Math.max(0.06, Math.min(1.1, power));
      this.mirrorMat.emissiveColor.set(0.64 * gain, 0.7 * gain, 0.67 * gain);
    }
    if (eye) {
      const dx = Math.max(-0.55, Math.min(0.55, eye.x - this.mirrorAt.x));
      const dy = Math.max(-0.35, Math.min(0.35, eye.y - this.mirrorAt.y));
      this.mirrorCam.position.set(
        this.mirrorAt.x + dx * 0.14,
        this.mirrorAt.y + dy * 0.14,
        this.mirrorAt.z + 0.035,
      );
      this.mirrorCam.setTarget(
        new Vector3(
          this.mirrorAt.x - dx * 0.65,
          this.mirrorAt.y - dy * 0.35 - 0.04,
          this.mirrorAt.z + 2.15,
        ),
      );
    }
  }

  /** Meshes to reveal momentarily during scene warmup so shaders never compile mid-scare. */
  warmupMeshes(): AbstractMesh[] {
    return [
      this.mirrorSteam,
      this.faucetStream,
      this.faucetSplash,
      ...this.ripples.map((r) => r.mesh),
      ...this.footprints,
    ];
  }

  setFaucetRunning(on: boolean): void {
    this.faucetRunning = on;
    this.faucetStream.isVisible = on;
    this.faucetSplash.isVisible = on;
  }

  triggerTankRipples(): void {
    for (const r of this.ripples) {
      r.age = -r.delay;
      r.active = true;
      r.mesh.scaling.set(0.14, 0.14, 1);
      r.mesh.visibility = 0;
      r.mesh.isVisible = false;
    }
  }

  /** Shows all wet footprints immediately (checkpoint restore) or steps them in gradually. */
  showWetFootprints(visible: boolean, gradual = false): void {
    if (!visible) {
      this.footprintRevealT = -1;
      for (const fp of this.footprints) {
        fp.isVisible = false;
        fp.visibility = 0;
      }
      return;
    }
    if (gradual) {
      this.footprintRevealT = 0;
      for (const fp of this.footprints) {
        fp.isVisible = false;
        fp.visibility = 0;
      }
    } else {
      this.footprintRevealT = -1;
      for (const fp of this.footprints) {
        fp.isVisible = true;
        fp.visibility = 1;
      }
    }
  }

  update(dt: number): void {
    this.clock += dt;
    if (this.faucetRunning) {
      const pulse = 0.88 + 0.12 * Math.sin(this.clock * 31) + 0.06 * Math.sin(this.clock * 53);
      this.faucetStream.scaling.set(pulse, 1, 2 - pulse);
      this.faucetMat.alpha = 0.38 + 0.08 * Math.sin(this.clock * 41);
      const sp = 0.82 + 0.28 * Math.abs(Math.sin(this.clock * 23));
      this.faucetSplash.scaling.set(sp, sp, 1);
      this.faucetSplash.rotation.y = this.clock * 2.4;
    }

    if (this.footprintRevealT >= 0) {
      this.footprintRevealT += dt;
      let allDone = true;
      this.footprints.forEach((fp, i) => {
        const start = i * 0.42;
        const p = Math.max(0, Math.min(1, (this.footprintRevealT - start) / 0.35));
        fp.isVisible = p > 0.01;
        fp.visibility = p;
        if (p < 1) allDone = false;
      });
      if (allDone) this.footprintRevealT = -1;
    }

    for (const r of this.ripples) {
      if (!r.active) continue;
      r.age += dt;
      if (r.age < 0) continue;
      const life = 2.1;
      const p = r.age / life;
      if (p >= 1) {
        r.active = false;
        r.mesh.isVisible = false;
        r.mesh.visibility = 0;
        continue;
      }
      r.mesh.isVisible = true;
      const scale = 0.12 + 0.92 * Math.pow(p, 0.72);
      r.mesh.scaling.set(scale, scale, 1);
      r.mesh.visibility = Math.sin(p * Math.PI) * (1 - p) * 0.42;
    }

    if (this.mirrorTex && !this.mirrorActive) {
      this.mirrorTex.refreshRate = RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
    } else if (this.mirrorTex && this.mirrorFastRefresh) {
      this.mirrorTex.refreshRate = 1;
    }
  }

  private populateMirrorRenderList(mirrorGlass: AbstractMesh): void {
    const rtt = this.mirrorTex;
    if (!rtt) return;
    const list: AbstractMesh[] = [];
    for (const m of this.scene.meshes) {
      if (m === mirrorGlass) continue;
      if (!m.isVisible || m.getTotalVertices() === 0) continue;
      if (/^bath_mirror_|pickup_volume|_contact_shadow|^vfx_|^studio_phone_cord/.test(m.name))
        continue;
      const b = m.getBoundingInfo().boundingBox;
      if (b.minimumWorld.z <= -11.5 && b.maximumWorld.z >= this.mirrorAt.z + 0.02) {
        list.push(m);
      }
    }
    rtt.renderList = list;
    if (this.mirrorRoomFill) {
      this.mirrorRoomFill.includedOnlyMeshes = [...list];
    }
  }

  /** Delicate tarnished mercury-glass foxing around the frame edges & humid bathroom mist. */
  private makeMirrorPatinaMaterial(): PBRMaterial {
    const tex = new DynamicTexture(
      "T_bath_mirror_steam",
      { width: 512, height: 640 },
      this.scene,
      true,
    );
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    const rand = seededRandom(19325);
    c.clearRect(0, 0, 512, 640);

    const edge = c.createRadialGradient(256, 310, 145, 256, 320, 355);
    edge.addColorStop(0, "rgba(18, 22, 20, 0)");
    edge.addColorStop(0.68, "rgba(14, 18, 16, 0.18)");
    edge.addColorStop(0.92, "rgba(10, 12, 11, 0.56)");
    edge.addColorStop(1, "rgba(6, 8, 7, 0.78)");
    c.fillStyle = edge;
    c.fillRect(0, 0, 512, 640);

    for (let i = 0; i < 240; i++) {
      const x = rand() * 512;
      const y = rand() * 640;
      const nearBorder = x < 55 || x > 457 || y < 55 || y > 585;
      const r = nearBorder ? 2 + rand() * 8 : 1 + rand() * 2.5;
      c.fillStyle = nearBorder
        ? `rgba(18, 20, 17, ${0.14 + rand() * 0.24})`
        : `rgba(165, 176, 170, ${0.02 + rand() * 0.04})`;
      c.beginPath();
      c.arc(x, y, r, 0, Math.PI * 2);
      c.fill();
    }

    const mist = c.createLinearGradient(0, 420, 0, 640);
    mist.addColorStop(0, "rgba(180, 192, 186, 0)");
    mist.addColorStop(1, "rgba(176, 188, 182, 0.16)");
    c.fillStyle = mist;
    c.fillRect(0, 420, 512, 220);

    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial("M_bath_mirror_steam", this.scene);
    mat.albedoTexture = tex;
    mat.opacityTexture = tex;
    mat.emissiveTexture = tex;
    mat.emissiveColor = new Color3(0.45, 0.48, 0.46);
    mat.disableLighting = true;
    mat.alpha = 0.72;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.disableDepthWrite = true;
    mat.backFaceCulling = false;
    mat.zOffset = -1;
    return mat;
  }

  private makeRippleMaterial(name: string, alpha: number): PBRMaterial {
    const tex = new DynamicTexture(`T_${name}`, 256, this.scene, true);
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    c.clearRect(0, 0, 256, 256);
    const g = c.createRadialGradient(128, 128, 72, 128, 128, 122);
    g.addColorStop(0, "rgba(180, 205, 200, 0)");
    g.addColorStop(0.55, "rgba(195, 218, 212, 0.72)");
    g.addColorStop(0.72, "rgba(225, 238, 232, 0.92)");
    g.addColorStop(0.86, "rgba(160, 184, 180, 0.35)");
    g.addColorStop(1, "rgba(140, 165, 162, 0)");
    c.fillStyle = g;
    c.fillRect(0, 0, 256, 256);
    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial(name, this.scene);
    mat.albedoTexture = tex;
    mat.opacityTexture = tex;
    mat.emissiveColor = new Color3(0.28, 0.34, 0.34);
    mat.disableLighting = true;
    mat.alpha = alpha;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.disableDepthWrite = true;
    mat.zOffset = -2;
    return mat;
  }

  private buildFootprints(): void {
    const tex = new DynamicTexture(
      "T_bath_wet_footprint",
      { width: 128, height: 256 },
      this.scene,
      true,
    );
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    c.clearRect(0, 0, 128, 256);
    const wet = (x: number, y: number, rx: number, ry: number, rot = 0, a = 0.72) => {
      c.save();
      c.translate(x, y);
      c.rotate(rot);
      const g = c.createRadialGradient(0, 0, 2, 0, 0, Math.max(rx, ry));
      g.addColorStop(0, `rgba(14, 15, 16, ${a})`);
      g.addColorStop(0.7, `rgba(18, 20, 21, ${a * 0.65})`);
      g.addColorStop(1, "rgba(18, 20, 21, 0)");
      c.fillStyle = g;
      c.beginPath();
      c.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
      c.fill();
      c.restore();
    };
    wet(64, 198, 23, 32, 0, 0.74);
    wet(76, 152, 13, 30, -0.1, 0.56);
    wet(62, 102, 28, 30, 0.08, 0.78);
    wet(39, 54, 10, 14, -0.08, 0.72);
    wet(56, 48, 7.5, 12, 0, 0.68);
    wet(70, 52, 7, 11, 0.06, 0.64);
    wet(82, 60, 6.5, 10, 0.12, 0.58);
    wet(92, 72, 5.5, 8.5, 0.18, 0.5);
    tex.hasAlpha = true;
    tex.update();

    const mat = new PBRMaterial("M_bath_wet_footprint", this.scene);
    mat.albedoColor = new Color3(0.04, 0.045, 0.05);
    mat.opacityTexture = tex;
    mat.metallic = 0;
    mat.roughness = 0.07;
    mat.alpha = 0.68;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.disableDepthWrite = true;
    mat.zOffset = -2;

    // Wet bare footprints stepping out of the bathroom across the back bedroom toward the doorway & phone
    const steps: [x: number, y: number, yaw: number, mirrorX: number][] = [
      [2.44, 13.78, 0.36, 1],
      [2.18, 13.24, 0.42, -1],
      [1.96, 12.66, 0.34, 1],
      [1.68, 12.06, 0.38, -1],
      [1.46, 11.42, 0.32, 1],
      [1.18, 10.72, 0.35, -1],
      [0.98, 10.05, 0.25, 1],
      [0.72, 9.48, 0.12, -1],
      [0.64, 8.85, -0.18, 1],
      [0.86, 8.22, -0.45, -1],
    ];
    steps.forEach(([bx, by, yaw, flip], i) => {
      const fp = CreatePlane(`bath_wet_footprint_${i}`, { width: 0.12, height: 0.25 }, this.scene);
      const pos = runtime(bx, by, 0.004);
      fp.position.copyFrom(pos);
      fp.rotation.set(Math.PI / 2, yaw, 0);
      fp.scaling.x = flip;
      fp.material = mat;
      fp.isPickable = false;
      fp.isVisible = false;
      fp.visibility = 0;
      this.footprints.push(fp);
    });
  }
}
