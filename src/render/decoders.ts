import { MeshoptCompression } from "@babylonjs/core/Meshes/Compression/meshoptCompression";
import { KhronosTextureContainer2 } from "@babylonjs/core/Misc/khronosTextureContainer2";

/**
 * Points Babylon's meshopt and KTX2 decoders at the copies served with the game
 * (public/vendor/, written by tools/vendor-decoders.mjs) instead of Babylon's CDN,
 * so assets load offline and the game has no run-time third-party dependency.
 * Call once before loading any .glb.
 */
export function useLocalDecoders(): void {
  const base = new URL(`${import.meta.env.BASE_URL}vendor/`, window.location.href).href;
  MeshoptCompression.Configuration = { decoder: { url: `${base}meshopt_decoder.js` } };

  const ktx2 = `${base}ktx2/`;
  KhronosTextureContainer2.URLConfig = {
    jsDecoderModule: `${ktx2}babylon.ktx2Decoder.js`,
    wasmUASTCToASTC: `${ktx2}uastc_astc.wasm`,
    wasmUASTCToBC7: `${ktx2}uastc_bc7.wasm`,
    wasmUASTCToRGBA_UNORM: `${ktx2}uastc_rgba8_unorm_v2.wasm`,
    wasmUASTCToRGBA_SRGB: `${ktx2}uastc_rgba8_srgb_v2.wasm`,
    wasmUASTCToR8_UNORM: `${ktx2}uastc_r8_unorm.wasm`,
    wasmUASTCToRG8_UNORM: `${ktx2}uastc_rg8_unorm.wasm`,
    jsMSCTranscoder: `${ktx2}msc_basis_transcoder.js`,
    wasmMSCTranscoder: `${ktx2}msc_basis_transcoder.wasm`,
    wasmZSTDDecoder: `${ktx2}zstddec.wasm`,
  };
}
