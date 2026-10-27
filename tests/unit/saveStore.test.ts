import { afterEach, expect, it, vi } from "vitest";
import { newGameSave } from "../../src/systems/saves/SaveData";
const idb = vi.hoisted(() => ({ setMany: vi.fn(), createStore: vi.fn(() => ({})) }));
vi.mock("idb-keyval", () => ({ ...idb, get: vi.fn(), set: vi.fn(), del: vi.fn() }));
import { SaveStore } from "../../src/systems/saves/SaveStore";
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});
it("atomically writes independent checkpoint and autosave keys before reporting success", async () => {
  vi.stubGlobal("window", { addEventListener: vi.fn(), removeEventListener: vi.fn() });
  let finish!: () => void;
  idb.setMany.mockReturnValueOnce(
    new Promise<void>((resolve) => {
      finish = resolve;
    }),
  );
  const status = vi.fn(),
    store = new SaveStore(status),
    data = newGameSave();
  data.inventory.matches = 10;
  const writing = store.saveCheckpoint(data);
  data.inventory.matches = 1;
  expect(store.saving).toBe(true);
  expect(status.mock.calls).toEqual([[true]]);
  const entries = idb.setMany.mock.calls[0][0] as [string, typeof data][];
  expect(entries.map(([key]) => key)).toEqual(["save.autosave", "save.checkpoint"]);
  expect(entries[0][1].inventory.matches).toBe(10);
  finish();
  await writing;
  expect(store.saving).toBe(false);
  expect(status).toHaveBeenLastCalledWith(false, "saved");
});
it("reports quota failure without claiming the progress was saved", async () => {
  vi.stubGlobal("window", { addEventListener: vi.fn(), removeEventListener: vi.fn() });
  idb.setMany.mockRejectedValueOnce(new Error("quota"));
  const status = vi.fn(),
    store = new SaveStore(status);
  await expect(store.saveCheckpoint(newGameSave())).rejects.toThrow("quota");
  expect(store.saving).toBe(false);
  expect(status).toHaveBeenLastCalledWith(false, "failed");
});
