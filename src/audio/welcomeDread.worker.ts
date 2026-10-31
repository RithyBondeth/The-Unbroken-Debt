/** Synthesises the title screen's sound off the main thread; see loadDread. */
import { synthesizeDread } from "./welcomeDread";

self.onmessage = (event: MessageEvent<number>) => {
  const bank = synthesizeDread(event.data);
  const arrays = [...bank.chant, ...bank.bed, ...Object.values(bank.stingers).flat()];
  (self as unknown as Worker).postMessage(
    bank,
    arrays.map((array) => array.buffer),
  );
};
