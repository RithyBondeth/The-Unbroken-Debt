import { describe, expect, it } from "vitest";
import { classifyDevice, type DeviceSignals } from "../../src/render/DeviceProfile";

const MAC =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/141.0 Safari/537.36";
const WIN =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/141.0 Safari/537.36";

const desktop = (gpu: Partial<DeviceSignals>, ua = WIN): DeviceSignals => ({
  webgpu: true,
  vendor: "",
  architecture: "",
  description: "",
  isFallbackAdapter: false,
  userAgent: ua,
  uaMobile: false,
  maxTouchPoints: 0,
  touchOnly: false,
  ...gpu,
});

describe("classifyDevice: who can play", () => {
  it("blocks phones", () => {
    const iphone = desktop(
      { vendor: "apple" },
      "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X)",
    );
    expect(classifyDevice(iphone).blocked).toBe("mobile");
    const android = desktop({ vendor: "qualcomm" }, "Mozilla/5.0 (Linux; Android 16) Mobile");
    expect(classifyDevice({ ...android, uaMobile: true }).blocked).toBe("mobile");
  });

  it("blocks iPads, which report a Mac user agent with a touch screen", () => {
    expect(classifyDevice(desktop({ vendor: "apple", maxTouchPoints: 5 }, MAC)).blocked).toBe(
      "mobile",
    );
  });

  it("blocks devices with no mouse or trackpad", () => {
    expect(classifyDevice(desktop({ vendor: "nvidia", touchOnly: true })).blocked).toBe("mobile");
  });

  it("blocks browsers without WebGPU and software renderers", () => {
    expect(classifyDevice(desktop({ webgpu: false })).blocked).toBe("no-webgpu");
    expect(classifyDevice(desktop({ isFallbackAdapter: true })).blocked).toBe("software-renderer");
    expect(classifyDevice(desktop({ vendor: "google", architecture: "swiftshader" })).blocked).toBe(
      "software-renderer",
    );
  });

  it("lets touch-screen laptops with a trackpad play", () => {
    expect(
      classifyDevice(desktop({ vendor: "intel", architecture: "gen-12lp", maxTouchPoints: 10 }))
        .blocked,
    ).toBeNull();
  });
});

describe("classifyDevice: starting preset", () => {
  const quality = (gpu: Partial<DeviceSignals>, ua?: string) =>
    classifyDevice(desktop(gpu, ua)).quality;

  it("puts integrated graphics on Low", () => {
    expect(quality({ vendor: "intel", architecture: "gen-12lp" })).toBe("low");
    expect(quality({ vendor: "intel", architecture: "xe-lpg" })).toBe("low");
    expect(
      quality({ vendor: "amd", architecture: "rdna-3", description: "amd radeon(tm) graphics" }),
    ).toBe("low");
    expect(quality({ vendor: "qualcomm", architecture: "adreno-x1" })).toBe("low");
  });

  it("starts Apple silicon on Medium (the M1 Pro reference machine)", () => {
    const apple = classifyDevice(desktop({ vendor: "apple", architecture: "metal-3" }, MAC));
    expect(apple).toMatchObject({ blocked: null, quality: "medium", integrated: true });
  });

  it("maps discrete GPU families to presets", () => {
    expect(quality({ vendor: "nvidia", architecture: "pascal" })).toBe("low");
    expect(quality({ vendor: "nvidia", architecture: "turing" })).toBe("medium");
    expect(quality({ vendor: "nvidia", architecture: "ampere" })).toBe("high");
    expect(quality({ vendor: "nvidia", architecture: "ada" })).toBe("ultra");
    expect(quality({ vendor: "amd", architecture: "rdna-2" })).toBe("medium");
    expect(quality({ vendor: "amd", architecture: "rdna-3" })).toBe("high");
    expect(quality({ vendor: "intel", architecture: "xe-hpg" })).toBe("medium");
  });

  it("starts unknown GPUs on Low, where dynamic resolution can only help", () => {
    expect(quality({ vendor: "", architecture: "" })).toBe("low");
  });
});
