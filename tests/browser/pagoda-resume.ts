/** Reloads the real archive produced by pagoda.html; never accesses player saves. */
import { Game } from "@/core/Game";
import { createEngine } from "@/render/createEngine";
import { detectDevice } from "@/render/detectDevice";
import { useLocalDecoders } from "@/render/decoders";
import { SaveStore } from "@/systems/saves/SaveStore";
import type { WhisperingPagoda } from "@/episodes/ep2/WhisperingPagoda";
async function run(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const status = document.getElementById("results")!;
  const saves = new SaveStore(undefined, "boon-sop-ep2-review");
  const before = (await saves.load("autosave")).save;
  if (before?.episode !== 2 || before.flags["ep2.complete"] !== true)
    throw new Error("Run the pagoda story journey first.");
  const oldEpisode = (await saves.load("episode1")).save;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", { value: saves });
  game.fade.waitForEnter = () => Promise.resolve();
  const url = new URL(location.href);
  url.search = "?continue";
  history.replaceState(null, "", url);
  await game.start({ audio: false });
  const until = performance.now() + 30000;
  while (!(window as unknown as { pagoda?: WhisperingPagoda }).pagoda?.active) {
    if (performance.now() > until) throw new Error("Episode 2 did not resume.");
    await new Promise((r) => setTimeout(r, 50));
  }
  const act = (window as unknown as { pagoda: WhisperingPagoda }).pagoda;
  const check = (ok: boolean, text: string) => {
    if (!ok) throw new Error(text);
    status.textContent += "\nPASS " + text;
  };
  check(
    game.episode === 2 && act.progress.stage === "complete",
    "Continue chooses the pagoda instead of Episode 1 CP5",
  );
  check(
    game.flags.get("series.respect", 0) === before.flags["series.respect"],
    "Completion reload does not award respect again",
  );
  check(
    game.inventory.has("silver_inlay") && game.inventory.has("blessed_thread"),
    "Second-seal remnant and white thread restored",
  );
  check(
    JSON.stringify((await saves.load("episode1")).save) === JSON.stringify(oldEpisode),
    "Episode 1 archive is unchanged on resume",
  );
  status.textContent += "\nPASS EPISODE 2 COMPLETION RELOAD";
}
void run().catch((error) => {
  document.getElementById("results")!.textContent += "\nFAIL " + String(error);
  console.error(error);
});
