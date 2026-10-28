import { describe, expect, it } from "vitest";
import en from "../../src/data/strings/en.json";
import km from "../../src/data/strings/km.json";
import { chooseLanguage, lookup, type StringKey } from "../../src/data/strings";

/** Keys and controls a hint names, which a translation must keep exactly. */
const CONTROLS = /\b(?:W A S D|Enter|Tab|Esc|CP\d|[EFQC])\b|←|→/g;
const controls = (text: string) => (text.match(CONTROLS) ?? []).sort();

describe("string tables", () => {
  it("has no Khmer keys that English lacks", () => {
    const extra = Object.keys(km).filter((key) => !(key in en));
    expect(extra).toEqual([]);
  });

  it("has no empty Khmer entries", () => {
    const empty = Object.entries(km).filter(([, text]) => !text.trim());
    expect(empty).toEqual([]);
  });

  it("keeps every control a hint names", () => {
    const changed = Object.entries(km)
      .filter(([key, text]) => {
        const english = en[key as StringKey];
        return english && controls(english).join() !== controls(text).join();
      })
      .map(([key]) => key);
    expect(changed).toEqual([]);
  });

  it("falls back to English for a missing entry", () => {
    expect(lookup({}, "start.enter")).toBe(en["start.enter"]);
    expect(lookup(km, "start.enter")).toBe(km["start.enter"]);
  });

  it("offers the Khmer draft only to development builds", () => {
    expect(chooseLanguage("?lang=km", true)).toBe("km");
    expect(chooseLanguage("?lang=km", false)).toBe("en");
    expect(chooseLanguage("", true)).toBe("en");
  });
});
