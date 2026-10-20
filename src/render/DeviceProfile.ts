import type { QualityName } from "./QualityPresets";

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
}

export type BlockReason = "no-webgpu" | "software-renderer" | "mobile";

export interface DeviceProfile {
  /** Null when the game can run; otherwise why it can't. */
  blocked: BlockReason | null;
  /** Starting preset. Dynamic resolution and the settings menu adjust from here. */
  quality: QualityName;
  /** Integrated graphics: shared memory, so the Low texture tier is used. */
  integrated: boolean;
  /** Human-readable summary for logs and the settings screen. */
  label: string;
}

/**
 * Decides whether the game runs on this device and which preset it starts on.
 * Policy (Development Plan, device scaling decision, October 2026): every
 * laptop and desktop with WebGPU plays, scaled by preset; phones and tablets
 * (including iPad) see the requirements page for Episode 1.
 */
export function classifyDevice(s: DeviceSignals): DeviceProfile {
  const label =
    [s.vendor, s.architecture, s.description].filter(Boolean).join(" · ") || "unknown GPU";
  const result = (
    blocked: BlockReason | null,
    quality: QualityName,
    integrated: boolean,
  ): DeviceProfile => ({
    blocked,
    quality,
    integrated,
    label,
  });

  if (isPhoneOrTablet(s)) return result("mobile", "low", true);
  if (!s.webgpu) return result("no-webgpu", "low", false);
  if (
    s.isFallbackAdapter ||
    /swiftshader|llvmpipe|software/.test(`${s.vendor} ${s.architecture} ${s.description}`)
  ) {
    return result("software-renderer", "low", false);
  }

  const { quality, integrated } = guessTier(s.vendor, s.architecture, s.description);
  return result(null, quality, integrated);
}

function isPhoneOrTablet(s: DeviceSignals): boolean {
  if (s.uaMobile === true) return true;
  if (/iPhone|iPad|iPod|Android|Mobile/i.test(s.userAgent)) return true;
  // iPadOS Safari reports a Mac user agent; a "Mac" with a touch screen is an iPad.
  if (/Macintosh/.test(s.userAgent) && s.maxTouchPoints > 1) return true;
  // No mouse or trackpad at all: the game's controls can't work.
  return s.touchOnly;
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
