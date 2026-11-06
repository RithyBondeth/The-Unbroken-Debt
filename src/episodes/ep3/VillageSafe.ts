import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import type { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { RelicCraft } from "../../shared/RelicCraft";
import type { Game } from "../../core/Game";
import { KHMER_DIGITS } from "./data/village";

/** Four real brass dials carry the same Khmer numerals as the accessible paper controls. */
export class VillageSafe {
  private readonly textures: DynamicTexture[] = [];
  private previous = "";
  constructor(game: Game) {
    const c = new RelicCraft(game.scene),
      root = c.root("safe_worked_dials", [0, -0.68, -25.32]);
    const brass = c.surface("safe_bronze", "#7e6b42", "metal");
    for (let i = 0; i < 4; i++) {
      const x = -0.43 + i * 0.27;
      const ring = c.ring(root, "safe_number_rim", 0.2, 0.018, [x, 0, 0], brass);
      ring.rotation.x = Math.PI / 2;
      ring.isPickable = false;
      const mat = c.mat("safe_digit_" + i, "#bbaa86");
      mat.albedoTexture = c.painted("safe_digit_" + i, () => undefined, 128);
      this.textures.push(mat.albedoTexture as DynamicTexture);
      const face = CreatePlane(
        "safe_khmer_digit_" + i,
        { size: 0.16, sideOrientation: 2 },
        game.scene,
      );
      face.parent = root;
      face.position.set(x, 0, 0.012);
      face.material = mat;
      face.isPickable = false;
    }
  }
  sync(values: readonly number[]): void {
    const key = values.join("");
    if (key === this.previous) return;
    this.previous = key;
    this.textures.forEach((texture, i) => {
      const ctx = texture.getContext() as CanvasRenderingContext2D;
      ctx.fillStyle = "#312c22";
      ctx.fillRect(0, 0, 128, 128);
      ctx.fillStyle = "#dfcba1";
      ctx.font = '76px "Preah Vihear", serif';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(KHMER_DIGITS[values[i]], 64, 68);
      texture.update();
    });
  }
}
