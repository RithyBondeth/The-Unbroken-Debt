import en from "./en.json";
import km from "./km.json";

export type StringKey = keyof typeof en;
export type Language = "en" | "km";

// Release builds leave the unreviewed Khmer draft out of the download altogether.
const TABLES: Record<Language, Partial<Record<StringKey, string>>> = {
  en,
  km: import.meta.env.DEV ? km : {},
};

/**
 * English, unless a development build asks for `?lang=km`. The Khmer table is
 * an unreviewed draft (docs/production/khmer-strings-review.csv), so it stays
 * out of release builds until a native speaker has approved it.
 */
export function chooseLanguage(search: string, dev: boolean): Language {
  return dev && new URLSearchParams(search).get("lang") === "km" ? "km" : "en";
}

export const language: Language = chooseLanguage(
  globalThis.location?.search ?? "",
  import.meta.env.DEV,
);
if (globalThis.document) document.documentElement.lang = language;

/** The string in the current language; missing Khmer entries fall back to English. */
export function lookup(table: Partial<Record<StringKey, string>>, key: StringKey): string {
  return table[key] ?? en[key];
}

export const t = (key: StringKey): string => lookup(TABLES[language], key);
