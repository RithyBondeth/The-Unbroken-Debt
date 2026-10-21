import strings from "../../data/strings/en.json";
import type { BlockReason } from "../../render/DeviceProfile";

/** Shown instead of the game when the device can't run it (see DeviceProfile). */
export function showRequirementsPage(root: HTMLElement, reason: BlockReason): void {
  root.innerHTML = `
    <section class="requirements">
      <h1>${strings["requirements.title"]}</h1>
      <p>${strings[`requirements.body.${reason}`]}</p>
      <dl>
        <dt>${strings["requirements.minimum"]}</dt><dd>${strings["requirements.minimum.value"]}</dd>
        <dt>${strings["requirements.recommended"]}</dt><dd>${strings["requirements.recommended.value"]}</dd>
        <dt>${strings["requirements.browser"]}</dt><dd>${strings["requirements.browser.value"]}</dd>
      </dl>
    </section>`;
  root.hidden = false;
}
