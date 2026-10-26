import { t } from "../../data/strings";
import type { BlockReason } from "../../render/DeviceProfile";

/** Shown instead of the game when the device can't run it (see DeviceProfile). */
export function showRequirementsPage(root: HTMLElement, reason: BlockReason): void {
  root.innerHTML = `
    <section class="requirements">
      <h1>${t("requirements.title")}</h1>
      <p>${t(`requirements.body.${reason}`)}</p>
      <dl>
        <dt>${t("requirements.minimum")}</dt><dd>${t("requirements.minimum.value")}</dd>
        <dt>${t("requirements.recommended")}</dt><dd>${t("requirements.recommended.value")}</dd>
        <dt>${t("requirements.browser")}</dt><dd>${t("requirements.browser.value")}</dd>
      </dl>
    </section>`;
  root.hidden = false;
}
