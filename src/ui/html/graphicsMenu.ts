import "./settings.css";
import type { DeviceProfile } from "@/render/DeviceProfile";
import {
  autoFrameRate,
  EFFECT_KEYS,
  needsReload,
  RENDER_SCALES,
  resolveGraphics,
  type EffectKey,
  type FrameCap,
  type GraphicsSettings,
  type PresetChoice,
} from "@/render/graphicsSettings";
import { QUALITY_ORDER, QUALITY_PRESETS, type QualityName } from "@/render/qualityPresets";

type Device = Pick<DeviceProfile, "quality" | "formFactor">;

export interface GraphicsMenuOptions {
  settings: GraphicsSettings;
  /** Null until the device check finishes (the title screen asks it in parallel). */
  device: Device | null;
  /**
   * In the pause menu: the settings the game loaded with. Quality and effects
   * shape loading itself, so a change to them says it applies on the next load.
   */
  loaded?: GraphicsSettings;
  onChange(next: GraphicsSettings): void;
}

export interface GraphicsMenu {
  /** Fills in "Auto" once the device is known. */
  setDevice(device: Device): void;
}

const NAMES: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  ultra: "Ultra",
};

const EFFECT_LABELS: Record<EffectKey, { label: string; note: string }> = {
  ssao: { label: "Ambient occlusion", note: "Soft contact shadows in corners and under objects." },
  volumetricFog: {
    label: "Volumetric fog",
    note: "The mist glows around the lamp and flames. Off: plain distance fog, much cheaper.",
  },
  taa: {
    label: "Temporal anti-aliasing",
    note: "Smooth, stable edges while still. Off: FXAA, sharper and cheaper.",
  },
};

/** Fallback while the device is unknown: what "Auto" would mean on a laptop. */
const UNKNOWN_DEVICE: Device = { quality: "low", formFactor: "desktop" };

/**
 * The graphics controls, shared by the title screen's settings and the pause
 * menu. Quality presets set the effects; changing an effect afterwards keeps
 * the player's choice until the preset changes.
 */
export function mountGraphicsMenu(
  container: HTMLElement,
  options: GraphicsMenuOptions,
): GraphicsMenu {
  let settings: GraphicsSettings = structuredClone(options.settings);
  let device = options.device;
  const section = document.createElement("section");
  section.className = "settings-graphics";
  section.setAttribute("aria-labelledby", "settings-graphics-title");
  container.append(section);

  const render = () => {
    const known = device ?? UNKNOWN_DEVICE;
    const resolved = resolveGraphics(settings, known).preset;
    const autoName = device ? NAMES[known.quality] : "detecting…";
    const autoFps = autoFrameRate(known.formFactor);
    const chosen = settings.preset === "auto" ? known.quality : settings.preset;
    const reload = options.loaded && needsReload(options.loaded, settings);

    section.innerHTML = `
      <h3 id="settings-graphics-title" class="settings-heading">Graphics</h3>
      <div class="settings-row">
        <label for="gfx-preset">Quality</label>
        <select id="gfx-preset" name="gfx-preset">
          ${option("auto", `Auto (${autoName})`, settings.preset)}
          ${QUALITY_ORDER.map((name) => option(name, NAMES[name], settings.preset)).join("")}
        </select>
      </div>
      <p class="settings-note">${escapeHtml(qualityNote(settings.preset, known, chosen))}</p>
      <div class="settings-row">
        <label for="gfx-scale">Resolution</label>
        <select id="gfx-scale" name="gfx-scale">
          ${RENDER_SCALES.map((scale) =>
            option(String(scale), `${Math.round(scale * 100)}%`, String(settings.renderScale)),
          ).join("")}
        </select>
      </div>
      <p class="settings-note">Share of up to ${resolved.maxRenderHeight}p rendered, then scaled to the screen. Lower is faster and softer.</p>
      ${checkbox("gfx-dynamic", "Dynamic resolution", settings.dynamicResolution)}
      <p class="settings-note">Lowers the resolution for a moment instead of dropping frames.</p>
      <div class="settings-row">
        <label for="gfx-fps">Frame rate</label>
        <select id="gfx-fps" name="gfx-fps">
          ${option("auto", `Auto (${autoFps} fps)`, settings.frameCap)}
          ${option("30", "30 fps · steady, cooler, longer battery", settings.frameCap)}
          ${option("60", "60 fps", settings.frameCap)}
          ${option("max", "Unlimited (display refresh)", settings.frameCap)}
        </select>
      </div>
      ${EFFECT_KEYS.map(
        (key) =>
          checkbox(`gfx-${key}`, EFFECT_LABELS[key].label, resolved[key]) +
          `<p class="settings-note">${EFFECT_LABELS[key].note}</p>`,
      ).join("")}
      <h3 class="settings-heading">Camera</h3>
      ${checkbox("gfx-headBob", "Head bob while walking", settings.headBob)}
      ${checkbox("gfx-cameraShake", "Camera shake (fear tremor, scare jolts)", settings.cameraShake)}
      ${checkbox("gfx-showFps", "Show frame rate", settings.showFps)}
      <p class="settings-reload" role="status" ${reload ? "" : "hidden"}>Quality and effect changes apply the next time the game loads, from your last checkpoint.</p>`;
  };

  const commit = (next: GraphicsSettings) => {
    settings = next;
    options.onChange(structuredClone(settings));
    const focused = document.activeElement?.id;
    render();
    if (focused) section.querySelector<HTMLElement>(`#${focused}`)?.focus({ preventScroll: true });
  };

  section.addEventListener("change", (event) => {
    const input = event.target as HTMLInputElement | HTMLSelectElement;
    const next = structuredClone(settings);
    const name = input.name.replace(/^gfx-/, "");
    const checked = input instanceof HTMLInputElement ? input.checked : false;
    switch (name) {
      case "preset":
        next.preset = input.value as PresetChoice;
        next.effects = {}; // a preset brings its own effects
        break;
      case "scale":
        next.renderScale = Number(input.value);
        break;
      case "dynamic":
        next.dynamicResolution = checked;
        break;
      case "fps":
        next.frameCap = input.value as FrameCap;
        break;
      case "headBob":
      case "cameraShake":
      case "showFps":
        next[name] = checked;
        break;
      default:
        if ((EFFECT_KEYS as readonly string[]).includes(name))
          next.effects[name as EffectKey] = checked;
        else return;
    }
    event.stopPropagation();
    commit(next);
  });

  render();
  return {
    setDevice(known) {
      device = known;
      render();
    },
  };
}

/** What the chosen quality is for; on Auto on a phone or tablet, what Auto did. */
function qualityNote(preset: PresetChoice, device: Device, chosen: QualityName): string {
  if (preset === "auto" && device.formFactor !== "desktop")
    return `Tuned for this ${device.formFactor}: ${NAMES[chosen]}, a lower render height and dynamic resolution that can go further down as it warms up.`;
  return QUALITY_PRESETS[chosen].target;
}

function option(value: string, label: string, current: string): string {
  return `<option value="${value}"${value === current ? " selected" : ""}>${escapeHtml(label)}</option>`;
}

function checkbox(id: string, label: string, checked: boolean): string {
  return `<label class="settings-row settings-check" for="${id}">${escapeHtml(label)}<input id="${id}" name="${id}" type="checkbox"${checked ? " checked" : ""}></label>`;
}

function escapeHtml(text: string): string {
  return text.replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!,
  );
}
