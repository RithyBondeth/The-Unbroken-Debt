/** Four original graphite studies, arranged TL Sora, TR Yay Mey, BL Sok, BR Vuthy. */
export const PORTRAIT_ATLAS = `${import.meta.env.BASE_URL}assets/ep1/notebook/people-graphite.png`;
export const PORTRAIT_CELLS: Readonly<Record<string, readonly [number, number]>> = {
  "P-SORA": [0, 0],
  "P-YAYMEY": [1, 0],
  "P-SOK": [0, 1],
  "P-VUTHY": [1, 1],
};
let atlas: HTMLImageElement | undefined;
let ready: Promise<void> | undefined;

/** Loaded once before book construction; never fetched or decoded during a page turn. */
export function loadNotebookPortraits(): Promise<void> {
  return (ready ??= (async () => {
    const image = new Image();
    image.src = PORTRAIT_ATLAS;
    try {
      await image.decode();
      atlas = image;
    } catch {
      // Keep notes usable if an optional illustration cannot be fetched.
      console.warn("Notebook portraits could not be loaded");
    }
  })());
}

export function paintNotebookPortrait(
  ctx: CanvasRenderingContext2D,
  id: string,
  x: number,
  y: number,
  width: number,
  height: number,
): void {
  const cell = PORTRAIT_CELLS[id];
  if (!atlas || !cell) return;
  const sw = atlas.naturalWidth / 2,
    sh = atlas.naturalHeight / 2;
  const size = Math.min(width, height);
  ctx.save();
  ctx.globalCompositeOperation = "multiply";
  ctx.drawImage(atlas, cell[0] * sw, cell[1] * sh, sw, sh, x + (width - size) / 2, y, size, size);
  ctx.restore();
}
