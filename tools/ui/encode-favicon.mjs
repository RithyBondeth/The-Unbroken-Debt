// Fits the painted favicon letter (paint-title.py `icon`) into the title's near-black
// square and writes each size. Run from the repository root:
//   node tools/ui/encode-favicon.mjs <letter.png> <out.png> <size> [<out.png> <size> ...]
import sharp from "sharp";

const [src, ...outputs] = process.argv.slice(2);
for (let i = 0; i < outputs.length; i += 2) {
  const out = outputs[i];
  const size = Number(outputs[i + 1]);
  const inner = Math.round(size * 0.86);
  const letter = await sharp(src)
    .resize(inner, inner, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .toBuffer();
  await sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 11, g: 10, b: 9, alpha: 1 },
    },
  })
    .composite([{ input: letter, gravity: "center" }])
    .png({ compressionLevel: 9 })
    .toFile(out);
}
