import { classifyDevice, type DeviceProfile, type DeviceSignals } from "./DeviceProfile";

interface UADataLike {
  mobile?: boolean;
}

/** Gathers device signals from the browser and classifies them (see DeviceProfile). */
export async function detectDevice(): Promise<DeviceProfile> {
  return classifyDevice(await readSignals());
}

async function readSignals(): Promise<DeviceSignals> {
  const nav = navigator as Navigator & { userAgentData?: UADataLike };
  const signals: DeviceSignals = {
    webgpu: false,
    vendor: "",
    architecture: "",
    description: "",
    isFallbackAdapter: false,
    userAgent: nav.userAgent,
    uaMobile: nav.userAgentData?.mobile ?? null,
    maxTouchPoints: nav.maxTouchPoints ?? 0,
    touchOnly:
      matchMedia("(any-pointer: coarse)").matches && !matchMedia("(any-pointer: fine)").matches,
  };

  if (!("gpu" in nav)) return signals;
  try {
    const adapter = await nav.gpu.requestAdapter({ powerPreference: "high-performance" });
    if (!adapter) return signals;
    const info = adapter.info as GPUAdapterInfo & { isFallbackAdapter?: boolean };
    signals.webgpu = true;
    signals.vendor = (info.vendor ?? "").toLowerCase();
    signals.architecture = (info.architecture ?? "").toLowerCase();
    signals.description = (info.description ?? "").toLowerCase();
    // Newer browsers report this on the info object; older ones on the adapter.
    signals.isFallbackAdapter =
      info.isFallbackAdapter ??
      (adapter as GPUAdapter & { isFallbackAdapter?: boolean }).isFallbackAdapter ??
      false;
  } catch {
    // An adapter request can throw in locked-down browsers; treat as no WebGPU.
  }
  return signals;
}
