import { describe, expect, it } from "vitest";
import {
  assertSave,
  newGameSave,
  SaveError,
  type SaveData,
} from "../../src/systems/saves/SaveData";
import { migrate } from "../../src/systems/saves/migrations";
import { crc32, decodeSaveCode, encodeSaveCode } from "../../src/systems/saves/saveCode";
import { endOfEpisodeOne } from "../../src/systems/saves/sampleSaves";

const reason = async (p: Promise<unknown>) => {
  try {
    await p;
    return "none";
  } catch (error) {
    return error instanceof SaveError ? error.reason : "other";
  }
};

describe("crc32", () => {
  it("matches the standard check value", () => {
    expect(crc32(new TextEncoder().encode("123456789")).toString(16)).toBe("cbf43926");
  });
});

describe("save codes", () => {
  it("round-trips a save exactly", async () => {
    const save = endOfEpisodeOne();
    const code = await encodeSaveCode(save);
    expect(code.startsWith("BS1.")).toBe(true);
    expect(await decodeSaveCode(code)).toEqual(save);
  });

  it("stays short enough to copy and paste for a whole episode", async () => {
    const code = await encodeSaveCode(endOfEpisodeOne());
    expect(code.length).toBeLessThan(1000);
    expect(code).toMatch(/^BS1\.[\w-]+\.[0-9a-z]+$/);
  });

  it("ignores spaces and line breaks from copying", async () => {
    const save = newGameSave(new Date("2026-10-20T12:00:00Z"));
    const code = await encodeSaveCode(save);
    const wrapped = `  ${code.slice(0, 20)}\n${code.slice(20)} `;
    expect(await decodeSaveCode(wrapped)).toEqual(save);
  });

  it("rejects a changed or mistyped code", async () => {
    const code = await encodeSaveCode(endOfEpisodeOne());
    const i = 10;
    const tampered = code.slice(0, i) + (code[i] === "A" ? "B" : "A") + code.slice(i + 1);
    expect(await reason(decodeSaveCode(tampered))).toBe("checksum");
  });

  it("rejects things that are not save codes", async () => {
    expect(await reason(decodeSaveCode("hello"))).toBe("format");
    expect(await reason(decodeSaveCode("BS2.abc.def"))).toBe("format");
  });
});

describe("validation", () => {
  it("accepts a new game and the end of Episode 1", () => {
    expect(() => assertSave(newGameSave())).not.toThrow();
    expect(() => assertSave(endOfEpisodeOne())).not.toThrow();
  });

  it("refuses damaged fields", () => {
    const damaged = (change: Partial<Record<keyof SaveData, unknown>>) => () =>
      assertSave({ ...endOfEpisodeOne(), ...change });
    expect(damaged({ checkpoint: "four" })).toThrow(SaveError);
    expect(damaged({ inventory: { matches: -2 } })).toThrow(SaveError);
    expect(damaged({ lamp: { oil: 2, state: "open" } })).toThrow(SaveError);
    expect(damaged({ flags: { "ep1.act": { nested: true } } })).toThrow(SaveError);
  });
});

describe("migrations", () => {
  const v1 = endOfEpisodeOne() as unknown as Record<string, unknown>;

  it("upgrades old saves step by step", () => {
    // A pretend version 0 that kept the oil as a percentage under another name.
    const v0 = { ...v1, saveVersion: 0, lamp: undefined, lampOilPercent: 64 };
    const migrations = {
      0: (s: Record<string, unknown>) => {
        const { lampOilPercent, ...rest } = s;
        return { ...rest, lamp: { oil: (lampOilPercent as number) / 100, state: "open" } };
      },
    };
    const upgraded = migrate(v0, migrations, 1);
    expect(upgraded.saveVersion).toBe(1);
    expect(upgraded.lamp).toEqual({ oil: 0.64, state: "open" });
    expect("lampOilPercent" in upgraded).toBe(false);
  });

  it("refuses saves from a newer game", () => {
    expect(() => migrate({ ...v1, saveVersion: 2 })).toThrow(/newer version/);
  });

  it("refuses versions with no upgrade path", () => {
    expect(() => migrate({ ...v1, saveVersion: 0 }, {}, 1)).toThrow(/No upgrade/);
  });
});
