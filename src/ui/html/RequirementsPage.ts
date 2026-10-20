import strings from "../../data/strings/en.json";

/** Shown instead of the game when WebGPU is not available. */
export function showRequirementsPage(root: HTMLElement): void {
  root.innerHTML = `
    <section class="requirements">
      <h1>${strings["requirements.title"]}</h1>
      <p>${strings["requirements.body"]}</p>
      <dl>
        <dt>${strings["requirements.minimum"]}</dt><dd>${strings["requirements.minimum.value"]}</dd>
        <dt>${strings["requirements.recommended"]}</dt><dd>${strings["requirements.recommended.value"]}</dd>
        <dt>${strings["requirements.browser"]}</dt><dd>${strings["requirements.browser.value"]}</dd>
      </dl>
    </section>`;
  root.hidden = false;
}
