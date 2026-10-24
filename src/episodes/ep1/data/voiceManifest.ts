export interface VoiceManifest {
  language: string;
  paragraphs: string[][];
}

/** Voice and subtitle languages are independent. A complete take prevents mixed-language paragraphs. */
export function parseVoiceManifest(input: unknown, paragraphs: number): VoiceManifest | null {
  if (!input || typeof input !== "object") return null;
  const manifest = input as Partial<VoiceManifest>;
  if (
    typeof manifest.language !== "string" ||
    !/^[a-z]{2,3}(?:-[A-Z]{2})?$/.test(manifest.language)
  )
    return null;
  if (!Array.isArray(manifest.paragraphs) || manifest.paragraphs.length !== paragraphs) return null;
  if (
    !manifest.paragraphs.every(
      (files) =>
        Array.isArray(files) &&
        files.length > 0 &&
        files.every(
          (file) =>
            typeof file === "string" &&
            /^assets\/ep1\/audio\/[\w./-]+\.(ogg|m4a|mp3|wav)$/.test(file) &&
            !file.split("/").includes(".."),
        ),
    )
  )
    return null;
  return {
    language: manifest.language,
    paragraphs: manifest.paragraphs.map((files) => [...files]),
  };
}
