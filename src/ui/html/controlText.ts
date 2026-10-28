/** Render control names consistently while preserving the original localized text. */
export function setControlText(node: HTMLElement, text: string): void {
  const pattern = /\b(W A S D|C \/ Ctrl|Enter|Shift|Ctrl|Tab|Esc|[EFQCR])\b/g;
  const parts: (string | HTMLElement)[] = [];
  let from = 0;
  for (const match of text.matchAll(pattern)) {
    parts.push(text.slice(from, match.index));
    const key = document.createElement("kbd");
    key.textContent = match[0];
    parts.push(key);
    from = match.index + match[0].length;
  }
  parts.push(text.slice(from));
  node.replaceChildren(...parts);
}
