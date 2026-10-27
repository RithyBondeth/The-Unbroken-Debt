import { afterEach, expect, it, vi } from "vitest";
import { Subtitles } from "../../src/ui/html/StoryUi";
interface FakeSubtitleNode {
  hidden: boolean;
  className: string;
  innerHTML: string;
  textContent: string;
  rendered: unknown[];
  setAttribute: (...args: unknown[]) => void;
  append: (...content: unknown[]) => void;
}
function fixture() {
  const nodes: FakeSubtitleNode[] = [];
  function create(): FakeSubtitleNode {
    const node: FakeSubtitleNode = {
      hidden: false,
      className: "",
      innerHTML: "",
      textContent: "",
      rendered: [] as unknown[],
      setAttribute: vi.fn(),
      append(...content: unknown[]) {
        this.rendered = content;
      },
    };
    nodes.push(node);
    return node;
  }
  vi.stubGlobal("document", { createElement: create, body: { appendChild: vi.fn() } });
  return { subtitles: new Subtitles(), node: nodes[0] };
}
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
it("does not let a stale timed subtitle hide or overwrite a timeline reply", async () => {
  vi.useFakeTimers();
  const { subtitles, node } = fixture();
  const old = subtitles.say(
    "Driver",
    "This first sentence is deliberately long enough to force another chunk. Do not show this next part.",
    5,
  );
  subtitles.show("Sora", "Who was that?");
  await vi.advanceTimersByTimeAsync(6000);
  await old;
  expect(node.hidden).toBe(false);
  expect(node.rendered[1]).toBe("Who was that?");
});
it("keeps the subtitle hidden after the timeline clears an older timed line", async () => {
  vi.useFakeTimers();
  const { subtitles, node } = fixture();
  const old = subtitles.say(
    "Driver",
    "Wait here. The rest of this line should not reappear after clearing the subtitle.",
    5,
  );
  subtitles.hide();
  await vi.advanceTimersByTimeAsync(6000);
  await old;
  expect(node.hidden).toBe(true);
});
