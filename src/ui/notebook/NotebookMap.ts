import { PATH } from "../../episodes/ep1/data/forestBorder";
import { ROAD_COVER } from "../../episodes/ep1/act1/EarlyStealthBrain";

export type MapShape =
  | { kind: "rect"; x: number; y: number; w: number; h: number; walls?: boolean; detail?: boolean }
  | { kind: "path"; points: number[][]; style?: "path" | "window" | "detail" | "door" }
  | { kind: "label"; x: number; y: number; text: string }
  | { kind: "you"; x: number; y: number; r: number };
export interface NotebookMap {
  title: string;
  bounds: [number, number, number, number];
  labelSize: number;
  /** Move the physical plan away from the binding without changing world coordinates. */
  bindingOffset: number;
  shapes: MapShape[];
  description: string;
}

export function notebookMap(
  studio: boolean,
  at: { x: number; y: number; z: number },
  sokOpen: boolean,
): NotebookMap {
  const shapes: MapShape[] = [];
  let bindingOffset: number;
  const rect = (x: number, y: number, w: number, h: number, walls = false) =>
    shapes.push({ kind: "rect", x, y, w, h, walls });
  const label = (x: number, y: number, text: string) => shapes.push({ kind: "label", x, y, text });
  const path = (points: number[][], style?: "path" | "window" | "detail" | "door") =>
    shapes.push({ kind: "path", points, style });
  let bounds: NotebookMap["bounds"], labelSize: number, title: string, description: string;
  if (studio) {
    bounds = [-6.45, -5.4, 6.9, 5.8];
    bindingOffset = -16;
    labelSize = 0.29;
    title = "Studio · Phnom Penh";
    rect(-6, -5, 6, 5, true);
    path(
      [
        [-6, -3],
        [-6, -2],
      ],
      "door",
    );
    rect(-3.65, -1.1, 1.3, 0.76);
    label(-4.3, -1.48, "Drawing table");
    path(
      [
        [-3.8, -1.35],
        [-3.4, -1.1],
      ],
      "detail",
    );
    rect(-0.68, -3.25, 0.66, 1.5);
    label(-1.4, -2.5, "Desk");
    label(-1.4, -2.17, "& drawer");
    rect(-5.9, -4.88, 1.9, 0.86);
    label(-4.7, -4.45, "Bed");
    shapes.push({ kind: "rect", x: -5.78, y: -4.77, w: 0.35, h: 0.62, detail: true });
    path(
      [
        [-5.3, -4.88],
        [-5.3, -4.02],
      ],
      "detail",
    );
    rect(-5.85, -3.75, 0.45, 0.55);
    path(
      [
        [-5.78, -3.64],
        [-5.5, -3.64],
        [-5.5, -3.56],
        [-5.78, -3.56],
      ],
      "detail",
    );
    label(-4.75, -3.48, "Phone");
    label(-5.1, -2.5, "Exit");
    // Door leaf and swing, distinct from the blue window on the south wall.
    path(
      [
        [-6, -3],
        [-5.15, -3],
      ],
      "door",
    );
    path(
      Array.from({ length: 17 }, (_, i) => [
        -6 + 0.85 * Math.cos((i * Math.PI) / 32),
        -3 + 0.85 * Math.sin((i * Math.PI) / 32),
      ]),
      "door",
    );
    rect(-3.7, -4.97, 2.5, 0.35);
    label(-2.35, -4.2, "Shelf / satchel");
    // A drawing sheet, pencil, and two desk drawers give furniture recognisable silhouettes.
    shapes.push({ kind: "rect", x: -3.45, y: -0.99, w: 0.55, h: 0.48, detail: true });
    path(
      [
        [-2.75, -0.99],
        [-2.75, -0.57],
      ],
      "detail",
    );
    path(
      [
        [-0.64, -2.75],
        [-0.06, -2.75],
      ],
      "detail",
    );
    path(
      [
        [-0.64, -2.25],
        [-0.06, -2.25],
      ],
      "detail",
    );
    path(
      [
        [-0.45, -3.02],
        [-0.25, -3.02],
      ],
      "detail",
    );
    path(
      [
        [-0.45, -2.52],
        [-0.25, -2.52],
      ],
      "detail",
    );
    path(
      [
        [-6, -5],
        [-6, -3.05],
      ],
      "detail",
    );
    path(
      [
        [-3.75, 0],
        [-2.25, 0],
      ],
      "window",
    );
    shapes.push({ kind: "you", x: at.x, y: at.z, r: 0.1 });
    description =
      "The drawing table stands by the window. The writing desk and its drawer are opposite the telephone and exit. A red dot marks your position.";
  } else if (at.z > 15) {
    bounds = [-9, -10, 80, 22];
    bindingOffset = -12;
    labelSize = 1.8;
    title = "Approach · Funeral courtyard";
    path(
      PATH.map(([x, z]) => [z, -x]),
      "path",
    );
    rect(-1, -4, 7, 8, true);
    label(3, -7.5, "Courtyard");
    label(3, 8, "Safe checkpoint");
    ROAD_COVER.forEach((r, i) => {
      rect(r.minZ, -r.maxX, r.maxZ - r.minZ, r.maxX - r.minX);
      label((r.minZ + r.maxZ) / 2, -6, `Cover ${3 - i}`);
    });
    label(60, -6, "Taxi");
    label(58, 8, "Flooded road");
    shapes.push({ kind: "you", x: at.z, y: -at.x || 0, r: 0.55 });
    description =
      "Follow the path left toward the funeral courtyard. Solid rectangles are carts you can crouch behind. The red dot is you; the presence is not shown.";
  } else {
    bounds = [-16, -11, 40, 22];
    bindingOffset = -24;
    labelSize = 0.95;
    title = "Village · House of mourning";
    rect(-6, -19, 12, 8, true);
    label(0, -21, "HOUSE · upper floor");
    path([
      [-1, -19],
      [-1, -11],
    ]);
    path([
      [-6, -13.5],
      [6, -13.5],
    ]);
    label(2.4, -16.6, "Hall");
    label(4.6, -14.8, "Phone");
    label(-3.5, -16.6, sokOpen ? "Sok’s room" : "Locked room");
    label(0, -11.6, "Stairs ↓");
    rect(-4, -7, 8, 6, true);
    label(0, -5.4, "FUNERAL TENT");
    label(0, -3.4, "Coffin / burner");
    label(-5.1, 1.4, "✦ Safe desk");
    label(0, 5, "Courtyard");
    path(
      [
        [0, 6],
        [0, 15],
      ],
      "path",
    );
    label(0, 12, "Path to taxi ↓");
    if (at.z >= -23) shapes.push({ kind: "you", x: at.x, y: at.z, r: 0.3 });
    // Furnishings distinguish the rooms and tent from anonymous rectangles.
    rect(-5.3, -18.5, 2.7, 1.6);
    rect(-0.7, -4.6, 1.4, 2.4);
    rect(-1.6, -1.8, 0.5, 0.5);
    for (let z = -11; z < -9; z += 0.35)
      path(
        [
          [-1, z],
          [1, z],
        ],
        "detail",
      );
    // Turn the long village axis across the spread, preserving positions and proportions.
    for (const shape of shapes) {
      if (shape.kind === "path") shape.points = shape.points.map(([x, y]) => [-y, x]);
      else if (shape.kind === "rect") {
        const { x, y, w, h } = shape;
        Object.assign(shape, { x: -y - h, y: x, w: h, h: w });
      } else {
        const { x, y } = shape;
        Object.assign(shape, { x: -y, y: x });
      }
    }
    // Labels remain horizontal and are placed around their landmarks after rotation.
    for (let i = shapes.length - 1; i >= 0; i--)
      if (shapes[i].kind === "label") shapes.splice(i, 1);
    label(15.5, -8, "HOUSE · upper floor");
    label(15.6, -2.3, sokOpen ? "Sok’s room" : "Locked room");
    label(16.6, 1.5, "Hall");
    label(14.8, 4.6, "Phone");
    label(10.5, 2.5, "Stairs");
    label(4, -5.3, "FUNERAL TENT");
    label(4, 2.8, "Coffin / burner");
    label(-1.4, -7.4, "✦ Safe desk");
    label(-5, -2.8, "Courtyard");
    label(-9, 3.3, "← Path to taxi");
    description =
      "The house is on the right; the path to the taxi is on the left. The red dot is you; a star marks the safe desk. The house plan shows the upper floor. Stairs face the courtyard; storage and water jars are beneath the house.";
  }
  return { title, bounds, labelSize, bindingOffset, shapes, description };
}

/** Relative widths keep architectural lines visible at every location's world scale. */
function mapShapeStyle(map: NotebookMap, shape: MapShape): { stroke: string; width: number } {
  const unit = map.bounds[2];
  if (shape.kind === "rect" && shape.walls) return { stroke: "#343024", width: unit * 0.006 };
  if (shape.kind === "path" && shape.style === "window")
    return { stroke: "#426b77", width: unit * 0.006 };
  if (
    (shape.kind === "path" && shape.style === "detail") ||
    (shape.kind === "rect" && shape.detail)
  )
    return { stroke: "#837865", width: unit * 0.0016 };
  return { stroke: "#423a2d", width: unit * 0.0038 };
}

const escape = (s: string) =>
  s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll('"', "&quot;");
export function mapSvg(map: NotebookMap): string {
  return `<svg viewBox="${map.bounds.join(" ")}" role="img" aria-label="${escape(map.title + ". " + map.description)}">${map.shapes
    .map((s) => {
      const style = mapShapeStyle(map, s);
      const stroke = `style="stroke:${style.stroke};stroke-width:${style.width};fill:none"`;
      if (s.kind === "rect")
        return `<rect x="${s.x}" y="${s.y}" width="${s.w}" height="${s.h}" class="${s.walls ? "walls" : ""}" style="stroke:${style.stroke};stroke-width:${style.width};fill:${s.walls ? "#e7ddc6" : "#dbd0b8"}"/>`;
      if (s.kind === "label")
        return `<text x="${s.x}" y="${s.y}" style="font-size:${map.labelSize}px;paint-order:stroke;stroke:#eee3cd;stroke-width:${map.labelSize * 0.2};stroke-linejoin:round">${escape(s.text)}</text>`;
      if (s.kind === "you") return `<circle cx="${s.x}" cy="${s.y}" r="${s.r}" class="you"/>`;
      return `<path d="${s.points.map(([x, y], i) => `${i ? "L" : "M"}${x} ${y}`).join(" ")}" class="${s.style ?? ""}" ${stroke}${s.style === "path" ? ` stroke-dasharray="${map.bounds[2] * 0.015} ${map.bounds[2] * 0.015}"` : ""}/>`;
    })
    .join("")}</svg>`;
}

/** The physical book and clear reader render the same geometry and player marker. */
export function paintNotebookMap(
  ctx: CanvasRenderingContext2D,
  map: NotebookMap,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  const [bx, by, bw, bh] = map.bounds;
  const scale = Math.min(width / bw, height / bh);
  ctx.save();
  ctx.translate(x + (width - bw * scale) / 2, y + (height - bh * scale) / 2);
  ctx.scale(scale, scale);
  ctx.translate(-bx, -by);
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  for (const s of map.shapes) {
    ctx.setLineDash([]);
    const style = mapShapeStyle(map, s);
    ctx.strokeStyle = style.stroke;
    ctx.lineWidth = style.width;
    if (s.kind === "rect") {
      ctx.fillStyle = s.walls
        ? "rgba(118,103,80,0.035)"
        : s.detail
          ? "rgba(255,255,255,0.12)"
          : "rgba(95,79,55,0.09)";
      ctx.fillRect(s.x, s.y, s.w, s.h);
      ctx.strokeRect(s.x, s.y, s.w, s.h);
    } else if (s.kind === "label") {
      ctx.fillStyle = "#201b15";
      ctx.font = `${map.labelSize}px "Patrick Hand"`;
      // A narrow paper halo separates labels from plan lines without opaque boxes.
      ctx.strokeStyle = "#e8dfcb";
      ctx.lineWidth = map.labelSize * 0.22;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.strokeText(s.text, s.x, s.y);
      ctx.fillText(s.text, s.x, s.y);
    } else if (s.kind === "you") {
      ctx.strokeStyle = "#e8dfcb";
      ctx.lineWidth = s.r * 0.8;
      ctx.fillStyle = "#9c3427";
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fill();
    } else {
      if (s.style === "path") ctx.setLineDash([bw * 0.015, bw * 0.015]);
      ctx.beginPath();
      s.points.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
      ctx.stroke();
    }
  }
  ctx.restore();
}
