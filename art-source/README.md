# art-source

Original, editable art files. **Install Git LFS first** (`git lfs install`): `.blend`, `.psd`, `.kra`, `.exr`, `.tif`, `.png` and `.wav` files here are stored with LFS (see `.gitattributes`).

| Folder | Contents |
|---|---|
| `blender/` | `.blend` scenes and models. One file per area (`ep1_area_house.blend`) or asset family. Follow the naming rules in the Technical Design Document, section 7. |
| `textures/` | Texture sources (painting files, high-resolution bakes) before export |
| `audio/` | Original 48 kHz / 24-bit WAV recordings and sessions (Audio Design Document, section 10) |
| `reference/` | Reference images for study only. **Not committed** (may be copyrighted); keep the source of each image in a text file beside it. |

Export from Blender into `art-export/`, then run `npm run assets` to produce the optimised files in `public/assets/`.
