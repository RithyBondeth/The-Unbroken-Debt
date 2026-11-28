import type { QualityName } from "./qualityPresets";

/**
 * What the browser tells us about the device, gathered once at boot.
 * Kept as plain data so the classification below can be unit-tested.
 */
export interface DeviceSignals {
  webgpu: boolean;
  /** WebGPU adapter info (lower-case). Browsers may leave fields empty for privacy. */
  vendor: string;
  architecture: string;
  description: string;
  isFallbackAdapter: boolean;
  userAgent: string;
  /** `navigator.userAgentData.mobile` where available (Chromium). */
  uaMobile: boolean | null;
  maxTouchPoints: number;
  /** True when no input device can point precisely (no mouse or trackpad). */
  touchOnly: boolean;
  /** Shorter side of the screen in CSS pixels (0 if unknown): tells phones from tablets. */
  screenShort: number;
}

/** "mobile": a phone or tablet whose browser has no WebGPU (the message names the ones that do). */
export type BlockReason = "no-webgpu" | "software-renderer" | "mobile";

export type FormFactor = "desktop" | "tablet" | "phone";

export interface DeviceProfile {
  /** Null when the game can run; otherwise why it can't. */
  blocked: BlockReason | null;
  /** Starting preset. Dynamic resolution and the settings menu adjust from here. */
  quality: QualityName;
  /** Integrated graphics: shared memory, so the Low texture tier is used. */
  integrated: boolean;
  /** Human-readable summary for logs and the settings screen. */
  label: string;
  /** Phones and tablets play with touch controls and start on lighter settings. */
  formFactor: FormFactor;
}

/**
 * Decides whether the game runs on this device and which preset it starts on.
 * Policy (Development Plan, device scaling decision, October 2026, widened in
 * November 2026): every laptop, desktop, phone and tablet with hardware WebGPU
 * plays, scaled by preset. Phones and tablets play with touch controls on the
 * Low preset, at a lower render height (graphicsSettings.ts).
 */
export function classifyDevice(s: DeviceSignals): DeviceProfile {
  const label =
    [s.vendor, s.architecture, s.description].filter(Boolean).join(" · ") || "unknown GPU";
  const formFactor = formFactorOf(s);
  const result = (
    blocked: BlockReason | null,
    quality: QualityName,
    integrated: boolean,
  ): DeviceProfile => ({
    blocked,
    quality,
    integrated,
    label,
    formFactor,
  });

  if (!s.webgpu) return result(formFactor === "desktop" ? "no-webgpu" : "mobile", "low", false);
  if (
    s.isFallbackAdapter ||
    /swiftshader|llvmpipe|software/.test(`${s.vendor} ${s.architecture} ${s.description}`)
  ) {
    return result("software-renderer", "low", false);
  }
  // Phone and tablet GPUs share memory and power with everything else: Low, and
  // the settings menu goes up from there.
  if (formFactor !== "desktop") return result(null, "low", true);

  const { quality, integrated } = guessTier(s.vendor, s.architecture, s.description);
  return result(null, quality, integrated);
}

/** Phones under 600 CSS pixels on their short side; tablets above. */
const PHONE_MAX_SHORT_SIDE = 600;

export function formFactorOf(s: DeviceSignals): FormFactor {
  const ua = s.userAgent;
  const small = s.screenShort > 0 && s.screenShort < PHONE_MAX_SHORT_SIDE;
  if (/iPhone|iPod/.test(ua)) return "phone";
  if (/iPad/.test(ua)) return "tablet";
  // iPadOS Safari (and an iPhone asking for the desktop site) reports a Mac user
  // agent; a "Mac" with a touch screen is one of them.
  if (/Macintosh/.test(ua) && s.maxTouchPoints > 1) return small ? "phone" : "tablet";
  // Android phones say "Mobile"; Android tablets don't.
  if (/Android/.test(ua)) return /Mobile/.test(ua) || s.uaMobile === true ? "phone" : "tablet";
  if (s.uaMobile === true || /Mobile/.test(ua))
    return small || s.screenShort === 0 ? "phone" : "tablet";
  // No mouse or trackpad at all (a Windows or ChromeOS tablet): touch controls.
  if (s.touchOnly) return small ? "phone" : "tablet";
  return "desktop";
}

/**
 * A starting guess from the GPU family. It errs low for unknown or ambiguous
 * hardware: dynamic resolution and the settings menu move up easily, while a
 * first launch that stutters makes a bad first impression.
 */
function guessTier(
  vendor: string,
  architecture: string,
  description: string,
): { quality: QualityName; integrated: boolean } {
  const arch = architecture;
  const desc = description;
  switch (vendor) {
    case "nvidia":
      if (/blackwell|ada/.test(arch)) return { quality: "ultra", integrated: false };
      if (/ampere/.test(arch)) return { quality: "high", integrated: false };
      if (/turing/.test(arch)) return { quality: "medium", integrated: false };
      return { quality: "low", integrated: false }; // Pascal and older
    case "amd": {
      // Ryzen APUs report "Radeon Graphics" without a model number.
      const integrated = /radeon(\(tm\))? graphics|vega \d+ graphics|\d{3}m\b/.test(desc);
      if (integrated) return { quality: "low", integrated: true };
      if (/rdna-?[34]/.test(arch)) return { quality: "high", integrated: false };
      if (/rdna/.test(arch)) return { quality: "medium", integrated: false };
      return { quality: "low", integrated: false }; // GCN
    }
    case "intel":
      // Arc discrete cards (Alchemist, Battlemage); everything else is integrated.
      if (/xe-hpg|alchemist|battlemage|\barc\b/.test(`${arch} ${desc}`) && !/xe-lpg/.test(arch)) {
        return { quality: "medium", integrated: false };
      }
      return { quality: "low", integrated: true };
    case "apple":
      // Browsers don't say which M-series chip. Start at Medium: right for the
      // Pro and Max chips (the M1 Pro is the reference machine); dynamic
      // resolution carries base chips.
      return { quality: "medium", integrated: true };
    case "qualcomm":
    case "arm":
      return { quality: "low", integrated: true }; // Snapdragon X laptops
    default:
      return { quality: "low", integrated: false };
  }
}
