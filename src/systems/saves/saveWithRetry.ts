/**
 * Writes a save, and when the browser refuses (storage full, private mode)
 * releases the mouse and asks the player before trying again. Progress is never
 * dropped: the loop only ends once the write succeeds.
 */
export async function saveWithRetry(
  write: () => Promise<void>,
  askToRetry: () => Promise<void>,
): Promise<void> {
  while (true) {
    try {
      await write();
      return;
    } catch {
      document.exitPointerLock();
      await askToRetry();
    }
  }
}
