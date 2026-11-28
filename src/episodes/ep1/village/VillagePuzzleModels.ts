import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateLathe } from "@babylonjs/core/Meshes/Builders/latheBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Scene } from "@babylonjs/core/scene";
import type { WardStationId } from "../data/villagePuzzles";

export interface BarberRadioRig {
  dialMat: PBRMaterial;
  dialLight: PointLight;
}

export interface WellRigHandles {
  sweepNode: TransformNode;
  bucketNode: TransformNode;
  ropeMesh: Mesh;
  attachedWeightNode: TransformNode;
  attachedHookNode: TransformNode;
}

export interface WardStationHandles {
  flameMesh: Mesh;
  light: PointLight;
  solvedGroup: TransformNode;
}

export interface HallClockHandles {
  hourHand: TransformNode;
  minuteHand: TransformNode;
  pendulumPivot: TransformNode;
}

/**
 * High-craft procedural PBR 3D props and hand-painted DynamicTexture artwork for all four
 * interconnected Episode 1 Village puzzles (matching `OfferingModels.ts` tactile craft).
 */
export class VillagePuzzleModels {
  private readonly mats = new Map<string, PBRMaterial>();
  private readonly textures: DynamicTexture[] = [];
  private serial = 0;

  constructor(private readonly scene: Scene) {}

  private mat(
    name: string,
    hex: string,
    roughness: number,
    metallic = 0,
    emissiveHex?: string,
  ): PBRMaterial {
    const existing = this.mats.get(name);
    if (existing) return existing;
    const m = new PBRMaterial(`M_vp_${name}`, this.scene);
    m.albedoColor = Color3.FromHexString(hex).toLinearSpace();
    m.roughness = roughness;
    m.metallic = metallic;
    m.maxSimultaneousLights = 8;
    if (emissiveHex) m.emissiveColor = Color3.FromHexString(emissiveHex).toLinearSpace();
    this.mats.set(name, m);
    return m;
  }

  private paintedMat(
    name: string,
    sizeW: number,
    sizeH: number,
    roughness: number,
    metallic: number,
    draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void,
    emissiveScale = 0,
    boxFrontFlip = false,
  ): PBRMaterial {
    const existing = this.mats.get(name);
    if (existing) return existing;
    const tex = new DynamicTexture(
      `T_vp_${name}`,
      { width: sizeW, height: sizeH },
      this.scene,
      true,
    );
    const ctx = tex.getContext() as unknown as CanvasRenderingContext2D;
    draw(ctx, sizeW, sizeH);
    tex.update(true);
    if (boxFrontFlip) {
      // Babylon's CreateBox +Z face maps UV rotated 180°; invert both axes so vertical posters/calendars read upright
      tex.uScale = -1;
      tex.uOffset = 1;
      tex.vScale = -1;
      tex.vOffset = 1;
    }
    this.textures.push(tex);
    const m = new PBRMaterial(`M_vp_${name}`, this.scene);
    m.albedoTexture = tex;
    m.albedoColor = Color3.White();
    m.roughness = roughness;
    m.metallic = metallic;
    m.maxSimultaneousLights = 8;
    if (emissiveScale > 0) {
      m.emissiveTexture = tex;
      m.emissiveColor = new Color3(emissiveScale, emissiveScale * 0.9, emissiveScale * 0.72);
    }
    this.mats.set(name, m);
    return m;
  }

  private box(
    parent: TransformNode,
    name: string,
    size: [number, number, number],
    pos: [number, number, number],
    mat: PBRMaterial,
    rot?: [number, number, number],
  ): Mesh {
    const m = CreateBox(
      `${name}_${this.serial++}`,
      { width: size[0], height: size[1], depth: size[2] },
      this.scene,
    );
    m.position.set(pos[0], pos[1], pos[2]);
    if (rot) m.rotation.set(rot[0], rot[1], rot[2]);
    m.material = mat;
    m.parent = parent;
    return m;
  }

  private cyl(
    parent: TransformNode,
    name: string,
    diameter: number,
    height: number,
    pos: [number, number, number],
    mat: PBRMaterial,
    rot?: [number, number, number],
    tessellation = 20,
  ): Mesh {
    const m = CreateCylinder(
      `${name}_${this.serial++}`,
      { diameter, height, tessellation },
      this.scene,
    );
    m.position.set(pos[0], pos[1], pos[2]);
    if (rot) m.rotation.set(rot[0], rot[1], rot[2]);
    m.material = mat;
    m.parent = parent;
    return m;
  }

  private lathe(
    parent: TransformNode,
    name: string,
    profile: [number, number][],
    pos: [number, number, number],
    mat: PBRMaterial,
    tessellation = 32,
  ): Mesh {
    const m = CreateLathe(
      `${name}_${this.serial++}`,
      {
        shape: profile.map(([r, y]) => new Vector3(r, y, 0)),
        tessellation,
        closed: true,
      },
      this.scene,
    );
    m.position.set(pos[0], pos[1], pos[2]);
    m.material = mat;
    m.parent = parent;
    return m;
  }

  private tube(
    parent: TransformNode,
    name: string,
    pts: [number, number, number][],
    radius: number,
    mat: PBRMaterial,
    tessellation = 12,
  ): Mesh {
    const m = CreateTube(
      `${name}_${this.serial++}`,
      {
        path: pts.map(([x, y, z]) => new Vector3(x, y, z)),
        radius,
        tessellation,
        cap: 3,
      },
      this.scene,
    );
    m.material = mat;
    m.parent = parent;
    return m;
  }

  // ------------------------------------------------------------------ Shared PBR Surface Materials
  private teakMat(): PBRMaterial {
    return this.paintedMat("teak_weathered", 256, 256, 0.84, 0.04, (ctx, w, h) => {
      ctx.fillStyle = "#3b281c";
      ctx.fillRect(0, 0, w, h);
      for (let i = 0; i < 65; i++) {
        ctx.fillStyle = i % 2 === 0 ? "rgba(22,13,8,0.34)" : "rgba(92,64,42,0.22)";
        ctx.fillRect(0, (i * 4.1) % h, w, 1 + (i % 3));
      }
      ctx.fillStyle = "rgba(18,12,8,0.18)";
      ctx.fillRect(0, h * 0.72, w, h * 0.28);
    });
  }

  private mahoganyMat(): PBRMaterial {
    return this.paintedMat("mahogany_lacquer", 256, 256, 0.42, 0.06, (ctx, w, h) => {
      const g = ctx.createLinearGradient(0, 0, 0, h);
      g.addColorStop(0, "#4c2216");
      g.addColorStop(0.5, "#3b190f");
      g.addColorStop(1, "#2a110a");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);
      for (let i = 0; i < 70; i++) {
        ctx.fillStyle = i % 3 === 0 ? "rgba(18,6,3,0.3)" : "rgba(116,58,36,0.16)";
        ctx.fillRect(0, (i * 3.7) % h, w, 1.5);
      }
    });
  }

  private brassAgedMat(): PBRMaterial {
    return this.mat("brass_aged", "#a98340", 0.36, 0.86);
  }

  private ironForgedMat(): PBRMaterial {
    return this.paintedMat("iron_forged", 256, 256, 0.62, 0.78, (ctx, w, h) => {
      ctx.fillStyle = "#302d2a";
      ctx.fillRect(0, 0, w, h);
      for (let i = 0; i < 180; i++) {
        const x = (i * 73) % w;
        const y = (i * 47) % h;
        ctx.fillStyle = i % 4 === 0 ? "rgba(118,52,26,0.34)" : "rgba(80,76,72,0.22)";
        ctx.fillRect(x, y, 4 + (i % 10), 4 + (i % 8));
      }
    });
  }

  private ropeMat(): PBRMaterial {
    return this.paintedMat("hemp_rope", 128, 128, 0.94, 0.02, (ctx, w, h) => {
      ctx.fillStyle = "#8a7554";
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "rgba(44,33,20,0.45)";
      ctx.lineWidth = 3;
      for (let i = -h; i < w + h; i += 8) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + h, h);
        ctx.stroke();
      }
    });
  }

  private redCordMat(): PBRMaterial {
    return this.mat("red_ward_cord", "#8c1b15", 0.86, 0.02);
  }

  private lateriteMat(): PBRMaterial {
    return this.paintedMat("laterite_rock", 256, 256, 0.94, 0.02, (ctx, w, h) => {
      ctx.fillStyle = "#5c3426";
      ctx.fillRect(0, 0, w, h);
      for (let i = 0; i < 260; i++) {
        const x = (i * 67 + 13) % w;
        const y = (i * 89 + 29) % h;
        const r = 2 + (i % 6);
        ctx.fillStyle = i % 3 === 0 ? "rgba(31,15,11,0.52)" : "rgba(130,72,48,0.32)";
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  }

  private ashMat(): PBRMaterial {
    return this.mat("incense_ash", "#7d776c", 0.98, 0.0);
  }

  // ------------------------------------------------------------------ 1. Compound Gate Bar & 3-Dial Brass Padlock
  buildGateLock(root: TransformNode): void {
    const teak = this.teakMat();
    const iron = this.ironForgedMat();
    const brass = this.brassAgedMat();

    // Heavy weathered cross-bars with iron end straps & carriage bolts
    for (const [name, y, thick] of [
      ["gate_bar_high", 1.54, 0.14],
      ["gate_bar_mid", 1.06, 0.15],
      ["gate_bar_low", 0.56, 0.13],
    ] as const) {
      this.box(root, name, [3.62, thick, 0.12], [0, y, 0], teak);
      for (const sx of [-1.52, 1.52]) {
        this.box(root, `${name}_strap`, [0.16, thick + 0.02, 0.14], [sx, y, 0], iron);
        this.cyl(root, `${name}_bolt`, 0.032, 0.16, [sx, y, 0], iron, [Math.PI / 2, 0, 0], 10);
      }
    }

    // Interlocking forged iron chain loops wrapping the center timbers
    for (const cx of [-0.46, 0.46]) {
      for (let i = 0; i < 8; i++) {
        const ly = 1.04 + i * 0.072;
        const link = CreateTorus(
          `gate_chain_${this.serial++}`,
          { diameter: 0.085, thickness: 0.017, tessellation: 14 },
          this.scene,
        );
        link.position.set(cx, ly, 0.085);
        link.scaling.set(0.65, 1.15, 0.85);
        link.rotation.y = i % 2 === 0 ? 0.15 : Math.PI / 2 + 0.15;
        link.material = iron;
        link.parent = root;
      }
    }
    // Cross-chain bridging the two verticals to the central padlock hasp
    this.tube(
      root,
      "gate_chain_bridge",
      [
        [-0.46, 1.48, 0.09],
        [-0.22, 1.44, 0.12],
        [0.0, 1.43, 0.13],
        [0.22, 1.44, 0.12],
        [0.46, 1.48, 0.09],
      ],
      0.018,
      iron,
    );

    // Sculpted 3-Dial Rusted Brass Padlock at center eye-line
    const lockRoot = new TransformNode(`gate_padlock_group_${this.serial++}`, this.scene);
    lockRoot.parent = root;
    lockRoot.position.set(0, 1.32, 0.14);

    // Curved hardened-steel U-shackle
    this.tube(
      lockRoot,
      "padlock_shackle",
      [
        [-0.055, 0.09, 0],
        [-0.055, 0.18, 0],
        [-0.035, 0.225, 0],
        [0.0, 0.24, 0],
        [0.035, 0.225, 0],
        [0.055, 0.18, 0],
        [0.055, 0.09, 0],
      ],
      0.016,
      iron,
    );
    // Beveled brass body casing + top/bottom collar plates
    this.box(lockRoot, "padlock_body", [0.18, 0.21, 0.075], [0, -0.01, 0], brass);
    this.box(lockRoot, "padlock_cap_top", [0.195, 0.028, 0.086], [0, 0.095, 0], brass);
    this.box(lockRoot, "padlock_cap_bot", [0.195, 0.028, 0.086], [0, -0.112, 0], brass);
    // Recessed dark tumbler window + 3 knurled brass digit wheels
    this.box(lockRoot, "padlock_slot", [0.135, 0.135, 0.016], [0, -0.01, 0.035], iron);
    const dialTex = this.paintedMat("padlock_wheel", 128, 128, 0.38, 0.82, (ctx, w, h) => {
      ctx.fillStyle = "#b7914a";
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#261a0e";
      ctx.font = "bold 20px Georgia, serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (let d = 0; d < 10; d++) {
        ctx.fillText(String(d), (d + 0.5) * (w / 10), h / 2);
      }
    });
    for (let i = 0; i < 3; i++) {
      const wy = 0.036 - i * 0.044;
      this.cyl(
        lockRoot,
        `padlock_wheel_${i}`,
        0.048,
        0.11,
        [0, wy, 0.036],
        dialTex,
        [0, 0, Math.PI / 2],
        18,
      );
    }

    // Rain-stained funeral gate notice pinned beside the lock
    const noticeMat = this.paintedMat(
      "gate_funeral_notice",
      512,
      512,
      0.92,
      0.0,
      (ctx, w, h) => {
        ctx.fillStyle = "#d5c7a3";
        ctx.fillRect(0, 0, w, h);
        // Rain tide stains
        ctx.fillStyle = "rgba(88,65,42,0.22)";
        ctx.fillRect(0, 0, w, 68);
        ctx.fillRect(0, h - 84, w, 84);
        ctx.strokeStyle = "#2c2118";
        ctx.lineWidth = 8;
        ctx.strokeRect(24, 24, w - 48, h - 48);
        ctx.lineWidth = 2;
        ctx.strokeRect(36, 36, w - 72, h - 72);
        ctx.fillStyle = "#1f1812";
        ctx.textAlign = "center";
        ctx.font = "bold 36px Georgia, serif";
        ctx.fillText("បុណ្យ ៧ ថ្ងៃ", w / 2, 118);
        ctx.font = "bold 28px Georgia, serif";
        ctx.fillText("HOUSE IN MOURNING", w / 2, 174);
        ctx.font = "22px Georgia, serif";
        ctx.fillStyle = "#3a2a1e";
        ctx.fillText("GATE SEALED AFTER DUSK", w / 2, 232);
        ctx.fillText("3-DIAL BRASS PADLOCK", w / 2, 276);
        ctx.fillStyle = "#7a1c15";
        ctx.font = "italic 24px Georgia, serif";
        ctx.fillText("Check roadside shops for", w / 2, 344);
        ctx.fillText("Uncle Sok’s three marks.", w / 2, 378);
        ctx.fillStyle = "rgba(95,38,24,0.28)";
        ctx.beginPath();
        ctx.arc(390, 420, 44, 0, Math.PI * 2);
        ctx.fill();
      },
      0,
      true,
    );
    this.box(
      root,
      "gate_notice_board",
      [0.34, 0.42, 0.014],
      [0.88, 1.48, 0.09],
      noticeMat,
      [0, 0, -0.04],
    );
    this.cyl(
      root,
      "gate_notice_nail",
      0.022,
      0.03,
      [0.88, 1.65, 0.1],
      iron,
      [Math.PI / 2, 0, 0],
      10,
    );

    // Full-doorway invisible pickup volume so looking straight at the gate focuses cleanly
    const pickup = this.box(root, "gate_lock_pickup", [3.4, 2.0, 0.5], [0, 1.25, 0.12], teak);
    pickup.visibility = 0;
  }

  // ------------------------------------------------------------------ 1b. Side Fence Red-Cord Ward
  buildSideFenceWard(root: TransformNode): void {
    const teak = this.teakMat();
    const cord = this.redCordMat();
    const iron = this.ironForgedMat();

    this.box(root, "loose_plank_a", [1.46, 0.22, 0.075], [0, 0.96, 0.22], teak, [0, 0, 0.035]);
    this.box(root, "loose_plank_b", [1.44, 0.22, 0.075], [0, 1.4, 0.22], teak, [0, 0, -0.025]);
    // Criss-crossed sacred crimson ward cord bound tightly around the loose planks
    this.tube(
      root,
      "ward_cord_diag_1",
      [
        [-0.64, 0.84, 0.265],
        [-0.2, 1.06, 0.275],
        [0.0, 1.18, 0.28],
        [0.24, 1.32, 0.275],
        [0.64, 1.5, 0.265],
      ],
      0.015,
      cord,
    );
    this.tube(
      root,
      "ward_cord_diag_2",
      [
        [-0.64, 1.5, 0.265],
        [-0.22, 1.3, 0.275],
        [0.0, 1.18, 0.288],
        [0.24, 1.04, 0.275],
        [0.64, 0.84, 0.265],
      ],
      0.015,
      cord,
    );
    this.tube(
      root,
      "ward_cord_wrap",
      [
        [-0.08, 1.16, 0.27],
        [0.0, 1.22, 0.295],
        [0.08, 1.16, 0.27],
        [0.0, 1.12, 0.295],
        [-0.08, 1.16, 0.27],
      ],
      0.016,
      cord,
    );
    // Dangling painted yantra talisman cloth strip tied at the center knot
    const talismanMat = this.paintedMat(
      "ward_talisman",
      128,
      256,
      0.9,
      0,
      (ctx, w, h) => {
        ctx.fillStyle = "#c9b892";
        ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = "#8a1c14";
        ctx.lineWidth = 4;
        ctx.strokeRect(12, 12, w - 24, h - 24);
        ctx.beginPath();
        ctx.arc(w / 2, h * 0.36, 30, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = "#7a1812";
        ctx.font = "bold 28px Georgia, serif";
        ctx.textAlign = "center";
        ctx.fillText("យ័ន្ត", w / 2, h * 0.68);
      },
      0,
      true,
    );
    this.box(
      root,
      "ward_talisman",
      [0.11, 0.26, 0.008],
      [0.02, 1.0, 0.28],
      talismanMat,
      [0.06, 0, -0.08],
    );
    for (const nx of [-0.62, 0.62]) {
      this.cyl(root, "plank_nail", 0.02, 0.04, [nx, 0.96, 0.25], iron, [Math.PI / 2, 0, 0], 8);
      this.cyl(root, "plank_nail", 0.02, 0.04, [nx, 1.4, 0.25], iron, [Math.PI / 2, 0, 0], 8);
    }
    const pickup = this.box(root, "side_fence_pickup", [1.65, 1.9, 0.55], [0, 1.2, 0.28], teak);
    pickup.visibility = 0;
  }

  // ------------------------------------------------------------------ 1c. Noodle Stall Khmer Calendar (Digit 7)
  buildNoodleCalendar(root: TransformNode): void {
    const teak = this.teakMat();
    const brass = this.brassAgedMat();

    // Compact angled wooden tabletop display easel resting cleanly on the Noodle Stall veranda table
    this.box(root, "cal_base", [0.28, 0.02, 0.14], [0, 0.01, 0], teak);
    this.box(root, "cal_back_board", [0.26, 0.32, 0.018], [0, 0.16, -0.02], teak, [-0.24, 0, 0]);
    this.box(root, "cal_strut", [0.04, 0.22, 0.018], [0, 0.12, -0.08], teak, [0.42, 0, 0]);
    this.box(root, "cal_clip", [0.16, 0.026, 0.024], [0, 0.3, -0.056], brass, [-0.24, 0, 0]);

    const calMat = this.paintedMat(
      "noodle_calendar_page",
      512,
      512,
      0.88,
      0.0,
      (ctx, w, h) => {
        ctx.fillStyle = "#dfd3b4";
        ctx.fillRect(0, 0, w, h);
        // Damp water stain along bottom
        ctx.fillStyle = "rgba(110,82,52,0.22)";
        ctx.fillRect(0, h - 90, w, 90);
        // Classic Cambodian red calendar header banner
        ctx.fillStyle = "#8e1c16";
        ctx.fillRect(20, 22, w - 40, 88);
        ctx.fillStyle = "#f2e5c6";
        ctx.textAlign = "center";
        ctx.font = "bold 36px Georgia, serif";
        ctx.fillText("ប្រតិទិន · ខែពិសាខ", w / 2, 66);
        ctx.font = "20px Georgia, serif";
        ctx.fillText("NOODLE STALL · 7TH NIGHT TALLY", w / 2, 98);

        // 7-column calendar grid
        const gx = 32;
        const gy = 132;
        const cw = (w - 64) / 7;
        const ch = 64;
        ctx.strokeStyle = "rgba(48,34,24,0.45)";
        ctx.lineWidth = 2;
        for (let r = 0; r < 5; r++) {
          for (let c = 0; c < 7; c++) {
            const day = r * 7 + c + 1;
            if (day > 30) continue;
            const x = gx + c * cw;
            const y = gy + r * ch;
            ctx.strokeRect(x, y, cw, ch);
            ctx.fillStyle = day === 7 ? "#7a0f0c" : "#2b2017";
            ctx.font = day === 7 ? "bold 38px Georgia, serif" : "26px Georgia, serif";
            ctx.fillText(String(day), x + cw / 2, y + ch * 0.64);
            if (day === 7) {
              // Hand-smeared red betel-juice ring around day 7!
              ctx.strokeStyle = "#a31410";
              ctx.lineWidth = 9;
              ctx.beginPath();
              ctx.ellipse(x + cw / 2, y + ch / 2, cw * 0.44, ch * 0.44, -0.14, 0, Math.PI * 2);
              ctx.stroke();
              ctx.fillStyle = "rgba(150,20,16,0.22)";
              ctx.fill();
              ctx.strokeStyle = "rgba(48,34,24,0.45)";
              ctx.lineWidth = 2;
            }
          }
        }
        ctx.fillStyle = "#5a1410";
        ctx.font = "italic 22px Georgia, serif";
        ctx.fillText("First mark — 7th night of mourning", w / 2, h - 28);
      },
      0,
      true,
    );

    this.box(root, "cal_paper", [0.23, 0.28, 0.01], [0, 0.16, -0.008], calMat, [-0.24, 0, 0]);
    const hit = this.box(root, "noodle_clue_hit", [0.46, 0.42, 0.36], [0, 0.18, 0], teak);
    hit.visibility = 0;
  }

  // ------------------------------------------------------------------ 1d. Barber Shop Vintage Valve Radio
  buildBarberRadio(root: TransformNode, worldPos: Vector3, initiallyOn: boolean): BarberRadioRig {
    const mahogany = this.mahoganyMat();
    const brass = this.brassAgedMat();
    const bakelite = this.mat("bakelite_black", "#181512", 0.28, 0.08);
    const chrome = this.mat("chrome_antenna", "#b8bdc2", 0.22, 0.92);

    // Stepped rubber feet + beveled mahogany cabinet
    for (const [fx, fz] of [
      [-0.19, -0.09],
      [0.19, -0.09],
      [-0.19, 0.09],
      [0.19, 0.09],
    ]) {
      this.cyl(root, "radio_foot", 0.036, 0.018, [fx, 0.009, fz], bakelite, undefined, 12);
    }
    this.box(root, "radio_cabinet", [0.46, 0.29, 0.24], [0, 0.16, 0], mahogany);
    this.box(root, "radio_crown", [0.48, 0.026, 0.26], [0, 0.312, 0], mahogany);
    this.box(root, "radio_plinth", [0.48, 0.022, 0.255], [0, 0.022, 0], mahogany);
    // Brass front trim frame
    this.box(root, "radio_bezel", [0.42, 0.24, 0.014], [0, 0.165, 0.12], brass);

    // Woven acoustic brass/linen speaker cloth on the left side
    const grilleMat = this.paintedMat("radio_grille", 256, 256, 0.85, 0.15, (ctx, w, h) => {
      ctx.fillStyle = "#534129";
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "rgba(182,146,84,0.45)";
      ctx.lineWidth = 3;
      for (let x = 0; x < w; x += 10) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      ctx.strokeStyle = "rgba(32,22,12,0.55)";
      for (let y = 0; y < h; y += 10) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
    });
    this.box(root, "radio_speaker_cloth", [0.22, 0.19, 0.016], [-0.085, 0.165, 0.125], grilleMat);
    for (let i = -2; i <= 2; i++) {
      this.box(
        root,
        `radio_slat_${i}`,
        [0.22, 0.012, 0.02],
        [-0.085, 0.165 + i * 0.036, 0.129],
        mahogany,
      );
    }

    // Illuminated amber glass tuning dial on the right side
    const dialMat = this.paintedMat(
      "radio_tuning_dial",
      512,
      256,
      0.2,
      0.05,
      (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, "#ffe49e");
        g.addColorStop(0.5, "#f0a943");
        g.addColorStop(1, "#9d561b");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = "#2b1608";
        ctx.lineWidth = 4;
        ctx.strokeRect(10, 10, w - 20, h - 20);
        // AM frequency ticks & markings
        ctx.fillStyle = "#261206";
        ctx.font = "bold 28px Georgia, serif";
        ctx.textAlign = "center";
        const freqs = ["550", "700", "900", "1200", "1600"];
        freqs.forEach((f, idx) => {
          const x = 56 + idx * 100;
          ctx.fillText(f, x, 92);
          ctx.fillRect(x - 2, 114, 4, 48);
        });
        for (let t = 0; t < 24; t++) {
          ctx.fillRect(42 + t * 18.5, 134, 2, 24);
        }
        ctx.font = "bold 22px Georgia, serif";
        ctx.fillText("PHNOM PENH · AM / SW", w / 2, 212);
        // Red tuning needle
        ctx.fillStyle = "#b81d13";
        ctx.fillRect(284, 34, 6, 156);
      },
      initiallyOn ? 0.95 : 0.05,
      true,
    );
    this.box(root, "radio_dial_glass", [0.165, 0.105, 0.014], [0.115, 0.2, 0.127], dialMat);

    // Three fluted Bakelite rotary control knobs with brass centers
    for (const [kx, label] of [
      [0.055, "vol"],
      [0.115, "tune"],
      [0.175, "band"],
    ] as const) {
      this.cyl(
        root,
        `radio_knob_${label}`,
        0.036,
        0.028,
        [kx, 0.09, 0.138],
        bakelite,
        [Math.PI / 2, 0, 0],
        16,
      );
      this.cyl(
        root,
        `radio_knob_cap_${label}`,
        0.018,
        0.032,
        [kx, 0.09, 0.14],
        brass,
        [Math.PI / 2, 0, 0],
        12,
      );
    }

    // Angled telescopic chrome antenna + ball tip
    this.cyl(root, "radio_antenna", 0.009, 0.56, [-0.18, 0.54, -0.08], chrome, [0, 0, -0.18], 10);
    const tip = CreateSphere(
      `radio_ant_tip_${this.serial++}`,
      { diameter: 0.022, segments: 10 },
      this.scene,
    );
    tip.position.set(-0.23, 0.81, -0.08);
    tip.material = chrome;
    tip.parent = root;

    // Warm amber backlight glowing gently on the Barber Shop veranda bench
    const dialLight = new PointLight(
      `barber_radio_glow_${this.serial++}`,
      new Vector3(worldPos.x, worldPos.y + 0.25, worldPos.z + 0.22),
      this.scene,
    );
    dialLight.diffuse.set(1.0, 0.68, 0.28);
    dialLight.range = 2.6;
    dialLight.intensity = initiallyOn ? 1.05 : 0;
    dialLight.shadowEnabled = false;

    const hit = this.box(root, "radio_pickup_hit", [0.68, 0.58, 0.52], [0, 0.24, 0.08], bakelite);
    hit.visibility = 0;

    return { dialMat, dialLight };
  }

  // ------------------------------------------------------------------ 1e. Moto Shop Workbench & Kerosene Ledger (Digit 2)
  buildMotoLedgerBench(root: TransformNode): void {
    const teak = this.teakMat();
    const iron = this.ironForgedMat();
    const brass = this.brassAgedMat();
    const coverMat = this.mat("ledger_cover", "#4e1d19", 0.72, 0.05);

    // Oil-stained wooden mechanic's workbench crate resting squarely on Moto Shop concrete floor (Y=0..0.78)
    this.box(root, "moto_bench_top", [0.82, 0.055, 0.56], [0, 0.75, 0], teak);
    this.box(root, "moto_bench_shelf", [0.74, 0.035, 0.48], [0, 0.24, 0], teak);
    for (const [lx, lz] of [
      [-0.36, -0.23],
      [0.36, -0.23],
      [-0.36, 0.23],
      [0.36, 0.23],
    ]) {
      this.box(root, "moto_bench_leg", [0.065, 0.74, 0.065], [lx, 0.37, lz], teak);
    }

    // Open stitched hardcover Kerosene Account Ledger resting cleanly at waist height (Y = 0.78)
    const bookRoot = new TransformNode(`moto_ledger_book_${this.serial++}`, this.scene);
    bookRoot.parent = root;
    bookRoot.position.set(-0.04, 0.78, 0.02);
    bookRoot.rotation.y = 0.16;

    this.box(bookRoot, "ledger_cover_l", [0.22, 0.014, 0.34], [-0.115, 0.007, 0], coverMat);
    this.box(bookRoot, "ledger_cover_r", [0.22, 0.014, 0.34], [0.115, 0.007, 0], coverMat);
    this.box(bookRoot, "ledger_spine", [0.04, 0.018, 0.345], [0, 0.008, 0], coverMat);

    const spreadMat = this.paintedMat("moto_ledger_spread", 512, 512, 0.9, 0.0, (ctx, w, h) => {
      // CreateBox +Y top face UVs sit 90 deg CW relative to front-facing root; rotate CCW so the open spread reads upright.
      ctx.save();
      ctx.translate(w / 2, h / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.translate(-w / 2, -h / 2);
      ctx.fillStyle = "#ddd1b0";
      ctx.fillRect(0, 0, w, h);
      // Spine shadow
      const sp = ctx.createLinearGradient(w / 2 - 26, 0, w / 2 + 26, 0);
      sp.addColorStop(0, "rgba(0,0,0,0)");
      sp.addColorStop(0.5, "rgba(35,22,12,0.42)");
      sp.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = sp;
      ctx.fillRect(w / 2 - 26, 0, 52, h);
      // Ruled blue ledger lines & red vertical margin
      ctx.strokeStyle = "rgba(42,84,128,0.28)";
      ctx.lineWidth = 2;
      for (let y = 76; y < h - 36; y += 28) {
        ctx.beginPath();
        ctx.moveTo(22, y);
        ctx.lineTo(w - 22, y);
        ctx.stroke();
      }
      ctx.strokeStyle = "rgba(150,36,28,0.45)";
      ctx.beginPath();
      ctx.moveTo(w * 0.42, 40);
      ctx.lineTo(w * 0.42, h - 30);
      ctx.stroke();

      // Left page entries
      ctx.fillStyle = "#221810";
      ctx.font = "bold 22px Georgia, serif";
      ctx.fillText("KEROSENE LEDGER", 28, 56);
      ctx.font = "19px Georgia, serif";
      ctx.fillText("Sok Family Farm", 28, 118);
      ctx.fillText("Lamp Oil · 4 tins", 28, 152);
      ctx.fillStyle = "#8a1610";
      ctx.font = "bold 30px Georgia, serif";
      ctx.fillText("LOT 2", 42, 224);
      ctx.strokeStyle = "#8a1610";
      ctx.lineWidth = 4;
      ctx.strokeRect(30, 188, 134, 52);

      // Right page cipher & vigil note
      ctx.fillStyle = "#241911";
      ctx.font = "bold 21px Georgia, serif";
      ctx.fillText("GATE LOCK ORDER", w / 2 + 22, 92);
      ctx.font = "bold 22px Georgia, serif";
      ctx.fillStyle = "#6e1712";
      ctx.fillText("1. Calendar", w / 2 + 28, 148);
      ctx.fillText("2. Knocks", w / 2 + 28, 186);
      ctx.fillText("3. Lot", w / 2 + 28, 224);
      ctx.fillStyle = "#241911";
      ctx.font = "italic 19px Georgia, serif";
      ctx.fillText("“Vigil begins one", w / 2 + 24, 316);
      ctx.fillText("hour past midnight.”", w / 2 + 24, 344);

      // Grease thumbprint smudge
      ctx.fillStyle = "rgba(42,32,20,0.22)";
      ctx.beginPath();
      ctx.arc(140, 390, 38, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });
    this.box(bookRoot, "ledger_pages", [0.4, 0.026, 0.31], [0, 0.02, 0], spreadMat);
    // Brass pencil resting beside the ledger
    this.cyl(
      root,
      "moto_pencil",
      0.011,
      0.18,
      [0.26, 0.785, 0.08],
      brass,
      [Math.PI / 2, 0, 0.4],
      6,
    );
    // Oil tin on lower shelf for grounded Moto Shop detail
    this.cyl(root, "moto_oil_can", 0.14, 0.22, [-0.18, 0.36, 0.02], iron, undefined, 16);

    const hit = this.box(root, "moto_ledger_hit", [0.76, 0.45, 0.56], [0, 0.92, 0], teak);
    hit.visibility = 0;
  }

  // ------------------------------------------------------------------ 1f. Moto Shop Forged Gooseneck Crowbar
  buildMotoCrowbar(root: TransformNode): void {
    const iron = this.ironForgedMat();
    const steelEdge = this.mat("crowbar_edge", "#7d7a74", 0.35, 0.9);

    // Leaning gooseneck forged iron pry-bar resting squarely on the floor (Y = 0..0.72)
    this.tube(
      root,
      "crowbar_body",
      [
        [-0.08, 0.02, 0.08],
        [-0.02, 0.22, 0.03],
        [0.04, 0.46, -0.02],
        [0.09, 0.68, -0.06],
        [0.14, 0.74, -0.08],
        [0.2, 0.72, -0.08],
        [0.24, 0.65, -0.08],
      ],
      0.017,
      iron,
      6,
    );
    // Split forked nail-puller claw tips
    this.box(
      root,
      "crowbar_claw_l",
      [0.055, 0.014, 0.018],
      [0.25, 0.63, -0.094],
      steelEdge,
      [0, 0, -0.9],
    );
    this.box(
      root,
      "crowbar_claw_r",
      [0.055, 0.014, 0.018],
      [0.25, 0.63, -0.066],
      steelEdge,
      [0, 0, -0.9],
    );
    // Chisel foot tip
    this.box(
      root,
      "crowbar_chisel",
      [0.045, 0.016, 0.038],
      [-0.09, 0.015, 0.09],
      steelEdge,
      [0.3, 0, 0.2],
    );

    const hit = this.box(root, "crowbar_hit", [0.5, 0.85, 0.4], [0.06, 0.4, 0], iron);
    hit.visibility = 0;
  }

  // ------------------------------------------------------------------ 2. Brick Well Bucket Rig, Counterweight & Grapple Hook
  buildWellRig(root: TransformNode): WellRigHandles {
    const teak = this.teakMat();
    const iron = this.ironForgedMat();
    const rope = this.ropeMat();
    const water = this.mat("well_dark_water", "#0b1416", 0.08, 0.15);

    const sweepNode = new TransformNode(`well_sweep_pivot_${this.serial++}`, this.scene);
    sweepNode.parent = root;
    sweepNode.position.set(0, 1.55, 0);

    // Dynamic attached laterite stone counterweight on the sweep butt (shown when attached!)
    const attachedWeightNode = new TransformNode(
      `well_attached_weight_${this.serial++}`,
      this.scene,
    );
    attachedWeightNode.parent = sweepNode;
    attachedWeightNode.position.set(0, -0.18, -1.15);
    this.buildLateriteBoulder(attachedWeightNode, 0.85);

    const bucketNode = new TransformNode(`well_bucket_rig_${this.serial++}`, this.scene);
    bucketNode.parent = root;
    bucketNode.position.set(0, 0.28, 0);

    // Stave-built tapered oak/teak well bucket
    this.lathe(
      bucketNode,
      "well_bucket_body",
      [
        [0.0, -0.17],
        [0.14, -0.17],
        [0.175, 0.17],
        [0.16, 0.17],
        [0.125, -0.14],
        [0.0, -0.14],
      ],
      [0, 0, 0],
      teak,
      20,
    );
    // Dark well water surface inside bucket
    this.cyl(bucketNode, "well_bucket_water", 0.3, 0.015, [0, 0.09, 0], water, undefined, 20);
    // Twin forged iron hoops + arched bail handle
    for (const [hy, rad] of [
      [-0.08, 0.153],
      [0.09, 0.172],
    ]) {
      const hoop = CreateTorus(
        `well_hoop_${this.serial++}`,
        { diameter: rad * 2, thickness: 0.015, tessellation: 22 },
        this.scene,
      );
      hoop.position.y = hy;
      hoop.material = iron;
      hoop.parent = bucketNode;
    }
    this.tube(
      bucketNode,
      "well_bail",
      [
        [-0.17, 0.16, 0],
        [-0.14, 0.28, 0],
        [0.0, 0.33, 0],
        [0.14, 0.28, 0],
        [0.17, 0.16, 0],
      ],
      0.011,
      iron,
    );

    // Dynamic forged iron grapple shackle right above the bucket bail (shown when attached!)
    const attachedHookNode = new TransformNode(`well_attached_hook_${this.serial++}`, this.scene);
    attachedHookNode.parent = bucketNode;
    attachedHookNode.position.set(0, 0.36, 0);
    this.buildGrappleMetal(attachedHookNode, 0.65);

    // Wet braided hemp haul rope running from the bucket bail straight up to the well beam
    const ropeMesh = this.cyl(root, "well_haul_rope", 0.022, 1.4, [0, 1.0, 0], rope, undefined, 10);

    const pickup = this.cyl(root, "well_rim_pickup", 3.4, 1.7, [0, 0.95, 0], teak, undefined, 16);
    pickup.visibility = 0;

    return { sweepNode, bucketNode, ropeMesh, attachedWeightNode, attachedHookNode };
  }

  buildWellWeight(root: TransformNode): void {
    this.buildLateriteBoulder(root, 1.0);
    const hit = this.box(
      root,
      "well_weight_hit",
      [0.6, 0.55, 0.6],
      [0, 0.24, 0],
      this.lateriteMat(),
    );
    hit.visibility = 0;
  }

  private buildLateriteBoulder(parent: TransformNode, scale: number): void {
    const stone = this.lateriteMat();
    const rope = this.ropeMat();
    // Multi-lobe organic porous laterite counterweight block bound in hemp rope
    const main = CreateSphere(
      `laterite_main_${this.serial++}`,
      { diameter: 0.36 * scale, segments: 10 },
      this.scene,
    );
    main.scaling.set(1.12, 0.78, 0.96);
    main.position.set(0, 0.15 * scale, 0);
    main.material = stone;
    main.parent = parent;
    const lobe = CreateSphere(
      `laterite_lobe_${this.serial++}`,
      { diameter: 0.24 * scale, segments: 8 },
      this.scene,
    );
    lobe.scaling.set(1.15, 0.85, 0.9);
    lobe.position.set(0.08 * scale, 0.12 * scale, -0.05 * scale);
    lobe.material = stone;
    lobe.parent = parent;
    // Criss-crossed rope harness + lifting eye loop on top
    for (const rotY of [0, Math.PI / 2]) {
      const band = CreateTorus(
        `weight_rope_${this.serial++}`,
        { diameter: 0.34 * scale, thickness: 0.026 * scale, tessellation: 18 },
        this.scene,
      );
      band.position.set(0, 0.15 * scale, 0);
      band.rotation.set(Math.PI / 2, rotY, 0);
      band.scaling.set(1.06, 0.82, 1.0);
      band.material = rope;
      band.parent = parent;
    }
    const loop = CreateTorus(
      `weight_eye_${this.serial++}`,
      { diameter: 0.12 * scale, thickness: 0.022 * scale, tessellation: 14 },
      this.scene,
    );
    loop.position.set(0, 0.31 * scale, 0);
    loop.rotation.x = Math.PI / 2;
    loop.material = rope;
    loop.parent = parent;
  }

  private buildGrappleMetal(parent: TransformNode, scale: number): void {
    const iron = this.ironForgedMat();
    this.cyl(
      parent,
      "grapple_shank",
      0.028 * scale,
      0.3 * scale,
      [0, 0.15 * scale, 0],
      iron,
      undefined,
      12,
    );
    const eye = CreateTorus(
      `grapple_eye_${this.serial++}`,
      { diameter: 0.075 * scale, thickness: 0.016 * scale, tessellation: 14 },
      this.scene,
    );
    eye.position.set(0, 0.32 * scale, 0);
    eye.rotation.x = Math.PI / 2;
    eye.material = iron;
    eye.parent = parent;
    // Three sweeping curved iron grapple flukes spaced 120° apart
    for (let i = 0; i < 3; i++) {
      const a = (i * Math.PI * 2) / 3;
      const ca = Math.cos(a);
      const sa = Math.sin(a);
      this.tube(
        parent,
        `grapple_fluke_${i}`,
        [
          [0, 0.02 * scale, 0],
          [ca * 0.075 * scale, -0.015 * scale, sa * 0.075 * scale],
          [ca * 0.135 * scale, 0.03 * scale, sa * 0.135 * scale],
          [ca * 0.145 * scale, 0.105 * scale, sa * 0.145 * scale],
        ],
        0.012 * scale,
        iron,
        8,
      );
    }
  }

  buildWellHook(root: TransformNode): void {
    const rope = this.ropeMat();
    // Stacked spiral hemp rope coil resting cleanly on the servants' hut plank floor
    for (let ring = 0; ring < 3; ring++) {
      const t = CreateTorus(
        `hook_coil_${this.serial++}`,
        { diameter: 0.34 - ring * 0.055, thickness: 0.034, tessellation: 24 },
        this.scene,
      );
      t.position.set(0, 0.02 + ring * 0.028, 0);
      t.material = rope;
      t.parent = root;
    }
    const hookHolder = new TransformNode(`hook_metal_tilt_${this.serial++}`, this.scene);
    hookHolder.parent = root;
    hookHolder.position.set(0.02, 0.09, 0.02);
    hookHolder.rotation.set(0.35, 0.5, 0.2);
    this.buildGrappleMetal(hookHolder, 1.0);

    const hit = this.box(root, "well_hook_hit", [0.65, 0.55, 0.65], [0, 0.22, 0], rope);
    hit.visibility = 0;
  }

  // ------------------------------------------------------------------ 3. Torn Betel Diagram, Sacred Thread, Marigold Dish & 3 Ward Stations
  buildTornDrawing(root: TransformNode): void {
    const teak = this.teakMat();
    // Low weathered wooden storage crate inside the servants' hut holding the torn drawing visibly
    this.box(root, "torn_crate", [0.54, 0.34, 0.44], [0, 0.17, 0], teak);

    const pageMat = this.paintedMat("torn_betel_half", 512, 512, 0.92, 0.0, (ctx, w, h) => {
      ctx.save();
      ctx.translate(w / 2, h / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.translate(-w / 2, -h / 2);
      ctx.fillStyle = "#dfd2b2";
      ctx.fillRect(0, 0, w, h);
      // Jagged dark shadow along torn left edge
      ctx.fillStyle = "#3a2b1e";
      ctx.beginPath();
      ctx.moveTo(0, 0);
      for (let y = 0; y <= h; y += 28) {
        ctx.lineTo(28 + ((y * 19) % 34), y);
      }
      ctx.lineTo(0, h);
      ctx.closePath();
      ctx.fill();
      // Right-half betel tray charcoal & red-ink diagram
      ctx.strokeStyle = "#2b1d14";
      ctx.lineWidth = 6;
      ctx.beginPath();
      ctx.arc(46, h * 0.48, 195, -Math.PI * 0.48, Math.PI * 0.48);
      ctx.stroke();
      // Sketched areca nuts on the right
      ctx.fillStyle = "#7a301c";
      for (const [ax, ay] of [
        [185, 210],
        [225, 245],
        [182, 275],
      ]) {
        ctx.beginPath();
        ctx.ellipse(ax, ay, 24, 15, 0.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      // Incense sticks at bottom front
      ctx.strokeStyle = "#8a1c14";
      ctx.lineWidth = 5;
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        ctx.moveTo(95 + i * 28, 390);
        ctx.lineTo(130 + i * 28, 468);
        ctx.stroke();
      }
      ctx.fillStyle = "#23160f";
      ctx.font = "bold 28px Georgia, serif";
      ctx.fillText("RIGHT · ARECA", 242, 232);
      ctx.fillText("FRONT · INCENSE", 212, 434);
      ctx.fillStyle = "#7c1a14";
      ctx.font = "italic 22px Georgia, serif";
      ctx.fillText("— Kanha’s Half", 272, 92);
      ctx.restore();
    });
    this.box(root, "torn_kanha_page", [0.28, 0.008, 0.34], [0, 0.348, 0], pageMat, [0, -0.22, 0]);
    const hit = this.box(root, "torn_drawing_hit", [0.6, 0.55, 0.5], [0, 0.32, 0], teak);
    hit.visibility = 0;
  }

  buildSacredThread(root: TransformNode): void {
    const teak = this.teakMat();
    const cotton = this.mat("sai_sin_cotton", "#ece4d0", 0.94, 0.0);
    const leaf = this.mat("banana_leaf_base", "#2d4c25", 0.72, 0.02);
    const red = this.redCordMat();

    // Small wooden kitchen tray + green banana leaf + spun white cotton sai sin skein
    this.lathe(
      root,
      "thread_tray",
      [
        [0, 0],
        [0.18, 0],
        [0.22, 0.032],
        [0.2, 0.036],
        [0.16, 0.012],
        [0, 0.012],
      ],
      [0, 0, 0],
      teak,
      24,
    );
    this.cyl(root, "thread_leaf", 0.32, 0.006, [0, 0.018, 0], leaf, undefined, 16);
    // Turned wooden spindle + thick wound white cotton loops
    this.cyl(root, "thread_spindle", 0.032, 0.22, [0, 0.055, 0], teak, [0, 0.3, Math.PI / 2], 12);
    for (let i = 0; i < 4; i++) {
      const skein = CreateTorus(
        `cotton_skein_${this.serial++}`,
        { diameter: 0.15 - i * 0.014, thickness: 0.032, tessellation: 20 },
        this.scene,
      );
      skein.position.set(0, 0.055 + i * 0.012, 0);
      skein.rotation.z = (i - 1.5) * 0.08;
      skein.material = cotton;
      skein.parent = root;
    }
    this.cyl(root, "thread_tie", 0.042, 0.02, [0.06, 0.068, 0], red, [0, 0, Math.PI / 2], 12);

    const hit = this.box(root, "thread_hit", [0.55, 0.38, 0.55], [0, 0.16, 0], teak);
    hit.visibility = 0;
  }

  buildMarigoldDish(root: TransformNode): void {
    const brass = this.brassAgedMat();
    const leaf = this.mat("marigold_leaf", "#284822", 0.7, 0.02);
    const goldA = this.mat("marigold_gold_a", "#e89a1c", 0.72, 0.02);
    const goldB = this.mat("marigold_gold_b", "#f4b429", 0.68, 0.02);

    // Repoussé Khmer brass phan pedestal dish
    this.lathe(
      root,
      "marigold_phan",
      [
        [0, 0],
        [0.11, 0],
        [0.085, 0.024],
        [0.042, 0.055],
        [0.055, 0.085],
        [0.19, 0.115],
        [0.21, 0.145],
        [0.195, 0.148],
        [0.165, 0.118],
        [0, 0.105],
      ],
      [0, 0, 0],
      brass,
      28,
    );
    this.cyl(root, "marigold_leaf_pad", 0.34, 0.008, [0, 0.115, 0], leaf, undefined, 18);
    // Lush mound of 9 multi-toned marigold flower heads
    const blossoms: [number, number, number, number][] = [
      [0, 0.175, 0, 0.095],
      [-0.085, 0.155, 0.03, 0.082],
      [0.085, 0.155, -0.02, 0.084],
      [0.02, 0.158, 0.085, 0.08],
      [-0.03, 0.156, -0.082, 0.082],
      [-0.095, 0.142, -0.055, 0.072],
      [0.092, 0.144, 0.062, 0.074],
      [0.045, 0.185, 0.032, 0.068],
      [-0.045, 0.184, -0.03, 0.07],
    ];
    blossoms.forEach(([x, y, z, d], idx) => {
      const fl = CreateSphere(
        `marigold_fl_${this.serial++}`,
        { diameter: d, segments: 10 },
        this.scene,
      );
      fl.scaling.set(1.08, 0.78, 1.04);
      fl.position.set(x, y, z);
      fl.material = idx % 2 === 0 ? goldA : goldB;
      fl.parent = root;
    });

    const hit = this.box(root, "marigold_hit", [0.55, 0.42, 0.55], [0, 0.18, 0], brass);
    hit.visibility = 0;
  }

  buildWardStation(
    root: TransformNode,
    stationId: WardStationId,
    worldPos: Vector3,
  ): WardStationHandles {
    const stone = this.lateriteMat();
    const brass = this.brassAgedMat();
    const ash = this.ashMat();
    const wax = this.mat("beeswax_candle", "#d6be80", 0.78, 0.0);
    const flameMat = this.mat("ward_candle_flame", "#ffb84d", 0.15, 0, "#ff9922");
    const emberMat = this.mat("incense_ember", "#ff4a18", 0.2, 0, "#ff3b10");
    const stickMat = this.mat("incense_stick_body", "#6d4829", 0.94, 0);
    const stickBase = this.mat("incense_stick_red", "#8f2119", 0.88, 0);

    // Carved low laterite offering plinth + fluted antique-brass Khmer incense censer
    this.box(root, `ward_plinth_${stationId}`, [0.58, 0.12, 0.52], [0, 0.06, 0], stone);
    this.lathe(
      root,
      `ward_censer_${stationId}`,
      [
        [0, 0.12],
        [0.12, 0.12],
        [0.09, 0.155],
        [0.15, 0.24],
        [0.165, 0.3],
        [0.145, 0.31],
        [0.125, 0.26],
        [0, 0.26],
      ],
      [0, 0, 0],
      brass,
      24,
    );
    this.cyl(root, `ward_ash_${stationId}`, 0.25, 0.02, [0, 0.275, 0], ash, undefined, 18);

    // Small beeswax offering candle beside the censer
    this.cyl(
      root,
      `ward_candle_${stationId}`,
      0.028,
      0.13,
      [-0.19, 0.185, 0.12],
      wax,
      undefined,
      12,
    );
    const flameMesh = CreateSphere(
      `ward_flame_${stationId}_${this.serial++}`,
      { diameter: 0.036, segments: 10 },
      this.scene,
    );
    flameMesh.scaling.set(0.75, 1.85, 0.75);
    flameMesh.position.set(-0.19, 0.278, 0.12);
    flameMesh.material = flameMat;
    flameMesh.isPickable = false;
    flameMesh.parent = root;

    // Solved offerings + exact ritual incense stick count (1 for ruin, 3 for neakta & stupas)
    const solvedGroup = new TransformNode(`ward_solved_${stationId}_${this.serial++}`, this.scene);
    solvedGroup.parent = root;

    const stickCount = stationId === "ruin" ? 1 : 3;
    const stickOffsets =
      stickCount === 1
        ? [[0, 0]]
        : [
            [-0.032, 0.01],
            [0, -0.015],
            [0.032, 0.01],
          ];
    stickOffsets.forEach(([sx, sz], i) => {
      const tilt = stickCount === 1 ? 0.06 : (i - 1) * 0.12;
      this.cyl(
        solvedGroup,
        `inc_red_${i}`,
        0.007,
        0.07,
        [sx, 0.31, sz],
        stickBase,
        [0, 0, tilt],
        8,
      );
      this.cyl(
        solvedGroup,
        `inc_body_${i}`,
        0.009,
        0.17,
        [sx - tilt * 0.12, 0.42, sz],
        stickMat,
        [0, 0, tilt],
        8,
      );
      const tip = CreateSphere(
        `inc_ember_${this.serial++}`,
        { diameter: 0.014, segments: 8 },
        this.scene,
      );
      tip.position.set(sx - tilt * 0.21, 0.505, sz);
      tip.material = emberMat;
      tip.isPickable = false;
      tip.parent = solvedGroup;
    });

    // Dedicated physical offering placed beside the censer once solved
    const offAnchor = new TransformNode(
      `ward_offering_placed_${stationId}_${this.serial++}`,
      this.scene,
    );
    offAnchor.parent = solvedGroup;
    offAnchor.position.set(0.18, 0.12, 0.08);
    if (stationId === "neakta") {
      // Clay bowl of cool well water
      this.lathe(
        offAnchor,
        "placed_water_bowl",
        [
          [0, 0],
          [0.075, 0],
          [0.11, 0.075],
          [0.095, 0.078],
          [0.065, 0.018],
          [0, 0.018],
        ],
        [0, 0, 0],
        stone,
        20,
      );
      this.cyl(
        offAnchor,
        "placed_water_fill",
        0.18,
        0.01,
        [0, 0.06, 0],
        this.mat("bowl_water", "#18282b", 0.08, 0.12),
        undefined,
        16,
      );
    } else if (stationId === "stupas") {
      const s = CreateTorus(
        `placed_thread_${this.serial++}`,
        { diameter: 0.13, thickness: 0.028, tessellation: 18 },
        this.scene,
      );
      s.position.y = 0.02;
      s.material = this.mat("sai_sin_cotton", "#ece4d0", 0.94, 0.0);
      s.parent = offAnchor;
    } else {
      const gold = this.mat("marigold_gold_a", "#e89a1c", 0.72, 0.02);
      this.cyl(offAnchor, "placed_m_dish", 0.17, 0.022, [0, 0.012, 0], brass, undefined, 16);
      for (const [mx, mz] of [
        [-0.03, 0.02],
        [0.035, -0.01],
        [0, 0.04],
      ]) {
        const fl = CreateSphere(
          `placed_m_fl_${this.serial++}`,
          { diameter: 0.062, segments: 8 },
          this.scene,
        );
        fl.position.set(mx, 0.045, mz);
        fl.material = gold;
        fl.parent = offAnchor;
      }
    }

    const light = new PointLight(
      `ward_light_${stationId}`,
      new Vector3(worldPos.x, worldPos.y + 0.45, worldPos.z),
      this.scene,
    );
    light.diffuse.set(1.0, 0.64, 0.24);
    light.range = 4.6;
    light.intensity = 0;
    light.shadowEnabled = false;

    const hit = this.box(root, `ward_hit_${stationId}`, [0.76, 0.68, 0.72], [0, 0.32, 0], stone);
    hit.visibility = 0;

    return { flameMesh, light, solvedGroup };
  }

  // ------------------------------------------------------------------ 4. 1930s Colonial Wall Pendulum Clock
  buildHallPendulumClock(root: TransformNode): HallClockHandles {
    const mahogany = this.mahoganyMat();
    const brass = this.brassAgedMat();
    const darkBack = this.mat("clock_recess", "#120c08", 0.9, 0.02);
    const steelHand = this.mat("clock_hand_steel", "#1a1816", 0.34, 0.84);

    // Molded colonial regulator clock body with pediment crown, finials, fluted pilasters & glazed pendulum box
    this.box(root, "clock_body_main", [0.46, 0.94, 0.16], [0, 0, 0], mahogany);
    this.box(root, "clock_crown_cornice", [0.54, 0.065, 0.21], [0, 0.48, 0.015], mahogany);
    this.box(root, "clock_crown_crest", [0.36, 0.09, 0.17], [0, 0.54, 0.005], mahogany);
    this.box(root, "clock_base_mould", [0.52, 0.06, 0.2], [0, -0.48, 0.012], mahogany);

    // Turned top central finial + twin side finials + bottom drop finial
    const finialProfile: [number, number][] = [
      [0.0, 0.0],
      [0.026, 0.0],
      [0.015, 0.025],
      [0.032, 0.06],
      [0.014, 0.095],
      [0.004, 0.135],
      [0.0, 0.14],
    ];
    this.lathe(root, "clock_finial_top", finialProfile, [0, 0.585, 0.01], mahogany, 16);
    this.lathe(root, "clock_finial_l", finialProfile, [-0.21, 0.51, 0.02], mahogany, 14);
    this.lathe(root, "clock_finial_r", finialProfile, [0.21, 0.51, 0.02], mahogany, 14);

    // Side fluted pilasters framing the case
    for (const px of [-0.205, 0.205]) {
      this.cyl(root, "clock_pilaster", 0.038, 0.86, [px, 0, 0.085], mahogany, undefined, 12);
    }

    // Lower pendulum window cavity + brass window frame
    this.box(root, "clock_pendulum_recess", [0.28, 0.42, 0.03], [0, -0.21, 0.072], darkBack);
    this.box(root, "clock_frame_l", [0.02, 0.44, 0.026], [-0.15, -0.21, 0.09], brass);
    this.box(root, "clock_frame_r", [0.02, 0.44, 0.026], [0.15, -0.21, 0.09], brass);
    this.box(root, "clock_frame_t", [0.32, 0.02, 0.026], [0, 0.0, 0.09], brass);
    this.box(root, "clock_frame_b", [0.32, 0.02, 0.026], [0, -0.42, 0.09], brass);

    // Spun antique-brass round dial bezel + 512px cracked enamel Roman-numeral clock face
    const bezel = CreateTorus(
      `clock_bezel_${this.serial++}`,
      { diameter: 0.35, thickness: 0.026, tessellation: 32 },
      this.scene,
    );
    bezel.position.set(0, 0.24, 0.095);
    bezel.rotation.x = Math.PI / 2;
    bezel.material = brass;
    bezel.parent = root;

    const dialMat = this.paintedMat(
      "hall_clock_enamel",
      512,
      512,
      0.45,
      0.02,
      (ctx, w, h) => {
        const cx = w / 2;
        const cy = h / 2;
        const gr = ctx.createRadialGradient(cx, cy, 40, cx, cy, 240);
        gr.addColorStop(0, "#ede2c8");
        gr.addColorStop(0.75, "#d8c7a2");
        gr.addColorStop(1, "#aa946c");
        ctx.fillStyle = gr;
        ctx.fillRect(0, 0, w, h);

        // Outer & inner railroad minute rings
        ctx.strokeStyle = "#1f1812";
        ctx.lineWidth = 5;
        ctx.beginPath();
        ctx.arc(cx, cy, 232, 0, Math.PI * 2);
        ctx.stroke();
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, 212, 0, Math.PI * 2);
        ctx.stroke();

        // 60 minute ticks
        for (let m = 0; m < 60; m++) {
          const a = (m / 60) * Math.PI * 2 - Math.PI / 2;
          const r0 = m % 5 === 0 ? 204 : 214;
          const r1 = 230;
          ctx.lineWidth = m % 5 === 0 ? 5 : 2;
          ctx.beginPath();
          ctx.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
          ctx.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
          ctx.stroke();
        }

        // Authentic Roman numerals
        const romans = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"];
        ctx.fillStyle = "#1b140f";
        ctx.font = "bold 40px Georgia, serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        romans.forEach((rn, idx) => {
          const a = (idx / 12) * Math.PI * 2 - Math.PI / 2;
          ctx.fillText(rn, cx + Math.cos(a) * 168, cy + Math.sin(a) * 168);
        });

        // Maker's inscription + hairline enamel crack
        ctx.font = "italic 18px Georgia, serif";
        ctx.fillStyle = "#3f3024";
        ctx.fillText("PHNOM PENH · 1932", cx, cy + 78);
        ctx.strokeStyle = "rgba(42,28,18,0.38)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx + 120, cy - 170);
        ctx.lineTo(cx + 55, cy - 68);
        ctx.lineTo(cx + 22, cy - 12);
        ctx.stroke();
      },
      0,
      true,
    );
    this.cyl(root, "clock_face", 0.34, 0.014, [0, 0.24, 0.088], dialMat, [Math.PI / 2, 0, 0], 32);

    // Sculpted filigree spade hour hand & lance minute hand
    const hourHand = new TransformNode(`clock_hour_pivot_${this.serial++}`, this.scene);
    hourHand.parent = root;
    hourHand.position.set(0, 0.24, 0.104);
    this.box(hourHand, "clock_hour_stem", [0.015, 0.098, 0.006], [0, 0.036, 0], steelHand);
    this.box(hourHand, "clock_hour_spade", [0.026, 0.026, 0.007], [0, 0.072, 0], steelHand, [
      0,
      0,
      Math.PI / 4,
    ]);

    const minuteHand = new TransformNode(`clock_min_pivot_${this.serial++}`, this.scene);
    minuteHand.parent = root;
    minuteHand.position.set(0, 0.24, 0.112);
    this.box(minuteHand, "clock_min_stem", [0.011, 0.145, 0.006], [0, 0.056, 0], steelHand);
    this.cyl(
      root,
      "clock_center_boss",
      0.026,
      0.022,
      [0, 0.24, 0.114],
      brass,
      [Math.PI / 2, 0, 0],
      14,
    );

    // Brass lyre pendulum pivoting cleanly from top of lower pendulum window
    const pendulumPivot = new TransformNode(`clock_pendulum_pivot_${this.serial++}`, this.scene);
    pendulumPivot.parent = root;
    pendulumPivot.position.set(0, 0.02, 0.09);
    this.cyl(pendulumPivot, "pend_rod_l", 0.009, 0.34, [-0.014, -0.17, 0], brass, undefined, 8);
    this.cyl(pendulumPivot, "pend_rod_r", 0.009, 0.34, [0.014, -0.17, 0], brass, undefined, 8);
    // Lenticular spun-brass pendulum bob
    const bob = CreateSphere(
      `pend_bob_${this.serial++}`,
      { diameter: 0.115, segments: 20 },
      this.scene,
    );
    bob.scaling.set(1.0, 1.0, 0.34);
    bob.position.set(0, -0.34, 0.004);
    bob.material = brass;
    bob.parent = pendulumPivot;

    const hit = this.box(root, "hall_clock_hit", [0.65, 1.25, 0.4], [0, 0.05, 0.1], mahogany);
    hit.visibility = 0;

    return { hourHand, minuteHand, pendulumPivot };
  }

  dispose(): void {
    for (const t of this.textures) t.dispose();
    for (const m of this.mats.values()) m.dispose();
    this.textures.length = 0;
    this.mats.clear();
  }
}
