import { SaveStore } from "../../systems/saves/SaveStore";
import { checkpointName } from "../../systems/saves/Checkpoints";
import { WelcomeAmbience } from "../../audio/WelcomeAmbience";
import "./welcome.css";
import { setControlText } from "./controlText";

export interface WelcomeSettings {
  sound: boolean;
  sensitivity: number;
  invertY: boolean;
}

const defaults: WelcomeSettings = { sound: true, sensitivity: 0.0022, invertY: false };
const settingsKey = "boon-sop.welcome-settings";

export function readWelcomeSettings(): WelcomeSettings {
  try {
    const saved = JSON.parse(
      localStorage.getItem(settingsKey) ?? "null",
    ) as Partial<WelcomeSettings> | null;
    return {
      sound: typeof saved?.sound === "boolean" ? saved.sound : defaults.sound,
      invertY: typeof saved?.invertY === "boolean" ? saved.invertY : defaults.invertY,
      sensitivity:
        typeof saved?.sensitivity === "number" && Number.isFinite(saved.sensitivity)
          ? Math.min(0.005, Math.max(0.0005, saved.sensitivity))
          : defaults.sensitivity,
    };
  } catch {
    return { ...defaults };
  }
}

/** A lightweight title screen: no engine, input capture or game audio until Start. */
export async function showWelcomeScreen(root: HTMLElement): Promise<WelcomeSettings> {
  const settings = readWelcomeSettings();
  root.hidden = false;
  root.innerHTML = `
    <main class="welcome" aria-label="The Unbroken Debt main menu">
      <div class="welcome-scene" aria-hidden="true"></div>
      <div class="welcome-weather" aria-hidden="true"><div class="welcome-atmosphere">
        <div class="welcome-rain"></div>
        <div class="welcome-lamp-glow"></div>
        <div class="welcome-lamp-flame"></div>
      </div></div>
      <div class="welcome-haze" aria-hidden="true"></div>
      <section class="welcome-content">
        <header class="welcome-brand">
          <p class="welcome-khmer" lang="km">បុណ្យសព៖ បំណុលមិនដាច់</p>
          <h1><img class="welcome-logo" src="/assets/ui/unbroken-debt-logo.png" alt="The Unbroken Debt" width="960" height="640"></h1>
          <p class="welcome-series">Boon Sop</p>
        </header>
        <nav class="welcome-menu" aria-label="Main menu">
          <button type="button" data-action="continue" disabled>Continue</button>
          <button type="button" data-action="new">New game</button>
          <button type="button" data-action="settings">Settings</button>
          <button type="button" data-action="controls">How to play</button>
          <button type="button" data-action="credits">Credits</button>
        </nav>
        <p class="welcome-status" role="status">Checking for a saved game…</p>
      </section>
      <footer class="welcome-footer">
        <p><span>Episode I</span> The House of Mourning</p>
        <div class="welcome-footer-actions">
          <button type="button" data-action="ambience" aria-pressed="false">Enable ambience</button>
          <button type="button" data-action="fullscreen">Fullscreen</button>
        </div>
      </footer>
      <dialog class="welcome-dialog" aria-labelledby="welcome-dialog-title"></dialog>
    </main>`;
  const menu = root.querySelector<HTMLElement>(".welcome-menu")!;
  const status = root.querySelector<HTMLElement>(".welcome-status")!;
  const resume = menu.querySelector<HTMLButtonElement>('[data-action="continue"]')!;
  const dialog = root.querySelector<HTMLDialogElement>("dialog")!;
  const ambience = new WelcomeAmbience(settings.sound);
  const soundButton = root.querySelector<HTMLButtonElement>('[data-action="ambience"]')!;
  const updateSoundButton = () => {
    const active = settings.sound && ambience.started;
    soundButton.textContent = active ? "Ambience on" : "Enable ambience";
    soundButton.setAttribute("aria-pressed", String(active));
  };
  const unlockAmbience = () => {
    void ambience.unlock().then(updateSoundButton);
  };
  let hasSave = false;
  try {
    const result = await new SaveStore().load("autosave");
    hasSave = result.save !== null;
    resume.disabled = !hasSave;
    status.textContent = result.problem
      ? "Your saved game could not be read. You can begin a new game."
      : hasSave
        ? `Continue: ${checkpointName(result.save!)} · ${result.save!.clock}`
        : "A debt waits to be repaid.";
  } catch {
    status.textContent = "Browser saves are unavailable. Progress may not be saved.";
  }
  menu.querySelector<HTMLButtonElement>("button:not(:disabled)")?.focus({ preventScroll: true });

  return new Promise((resolve) => {
    const abort = new AbortController();
    const listen = { signal: abort.signal };
    const visibility = () => {
      const visible = !document.hidden;
      ambience.setVisible(visible);
      root.querySelector(".welcome")?.classList.toggle("welcome-paused", !visible);
    };
    document.addEventListener("visibilitychange", visibility, listen);
    visibility();
    window.addEventListener(
      "pagehide",
      (event) => {
        if (event.persisted) ambience.setVisible(false);
        else ambience.dispose();
      },
      listen,
    );
    window.addEventListener("pageshow", visibility, listen);
    const gesture = (event: Event) => {
      const target = event.target as HTMLElement;
      if (target.closest('[data-action="ambience"], input[name="sound"]')) return;
      unlockAmbience();
    };
    root.addEventListener("pointerdown", gesture, listen);
    root.addEventListener("keydown", gesture, listen);
    const start = (continuing: boolean) => {
      abort.abort();
      ambience.dispose();
      soundButton.disabled = true;
      dialog.close();
      const url = new URL(location.href);
      url.searchParams.delete("continue");
      if (continuing) url.searchParams.set("continue", "");
      history.replaceState(null, "", url);
      menu.hidden = true;
      status.textContent = continuing ? "Returning to your saved place…" : "Entering the darkness…";
      root.querySelector(".welcome")?.classList.add("welcome-loading");
      root.querySelector<HTMLButtonElement>('[data-action="fullscreen"]')!.disabled = true;
      resolve({ ...settings });
    };
    const open = (title: string, body: string) => {
      dialog.innerHTML = `<h2 id="welcome-dialog-title">${title}</h2>${body}<form method="dialog"><button class="welcome-back">Back</button></form>`;
      for (const control of dialog.querySelectorAll<HTMLElement>(".welcome-controls dt")) {
        setControlText(control, control.textContent ?? "");
      }
      dialog.showModal();
    };
    root.addEventListener(
      "click",
      (event) => {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>(
          "button[data-action]",
        );
        if (!button || button.disabled) return;
        switch (button.dataset.action) {
          case "continue":
            start(true);
            break;
          case "new":
            if (!hasSave) start(false);
            else
              open(
                "Begin again?",
                `<p>Starting a new game will replace your autosave when you reach a checkpoint.</p><button data-action="confirm-new">Begin new game</button>`,
              );
            break;
          case "confirm-new":
            start(false);
            break;
          case "settings":
            open(
              "Settings",
              `
            <label class="welcome-setting">Sound <input name="sound" type="checkbox" ${settings.sound ? "checked" : ""}></label>
            <p class="welcome-note">Controls menu ambience and game sound. Headphones recommended.</p>
            <label class="welcome-setting" for="welcome-sensitivity">Mouse sensitivity</label>
            <input id="welcome-sensitivity" name="sensitivity" aria-label="Mouse sensitivity" type="range" min="0.0005" max="0.005" step="0.0001" value="${settings.sensitivity}">
            <label class="welcome-setting">Invert vertical look <input name="invertY" type="checkbox" ${settings.invertY ? "checked" : ""}></label>`,
            );
            break;
          case "controls":
            open(
              "How to play",
              `<p>Return to the house. Listen closely. Keep your lamp near.</p><dl class="welcome-controls"><dt>W A S D</dt><dd>Move</dd><dt>Mouse</dt><dd>Look</dd><dt>E</dt><dd>Interact / record at a safe writing desk</dd><dt>Shift</dt><dd>Hurry</dd><dt>C / Ctrl</dt><dd>Hold to crouch</dd><dt>F</dt><dd>Light or put out the lamp</dd><dt>Q</dt><dd>Notebook: objective, map, clues and people</dd><dt>Tab</dt><dd>Satchel</dd></dl><p class="welcome-note">Progress saves at checkpoints. Being caught returns you to your last safe checkpoint. Click inside the game to capture your mouse. Escape releases it.</p>`,
            );
            break;
          case "credits":
            open(
              "Boon Sop",
              `<p>The Unbroken Debt</p><p>A game by Rithy Bondeth.</p><p class="welcome-note">Built with Babylon.js and Havok. Ubuntu font by Canonical; Preah Vihear by Danh Hong. Patrick Hand and Freehand are used in Sora’s sketchbook.</p><p class="welcome-note">Library assets from Poly Haven, character bases from the MakeHuman Community and sounds from Kenney (all CC0). Archive photographs by Léon Busy, 1921, Albert Kahn Museum (CC0).</p><p class="welcome-note">Title artwork created with OpenAI image generation.</p>`,
            );
            break;
          case "fullscreen":
            void (
              document.fullscreenElement
                ? document.exitFullscreen()
                : document.documentElement.requestFullscreen()
            ).catch(() => {
              status.textContent = "Fullscreen is unavailable in this browser window.";
            });
            break;
          case "ambience":
            settings.sound = !(settings.sound && ambience.started);
            ambience.setEnabled(settings.sound);
            if (settings.sound) unlockAmbience();
            updateSoundButton();
            try {
              localStorage.setItem(settingsKey, JSON.stringify(settings));
            } catch {
              /* Session only. */
            }
            break;
        }
      },
      listen,
    );
    dialog.addEventListener(
      "change",
      (event) => {
        const input = event.target as HTMLInputElement;
        if (input.name === "sound") {
          settings.sound = input.checked;
          ambience.setEnabled(settings.sound);
          if (settings.sound) unlockAmbience();
          updateSoundButton();
        }
        if (input.name === "invertY") settings.invertY = input.checked;
        if (input.name === "sensitivity") settings.sensitivity = Number(input.value);
        try {
          localStorage.setItem(settingsKey, JSON.stringify(settings));
        } catch {
          /* Session settings still apply. */
        }
      },
      listen,
    );
    menu.addEventListener(
      "keydown",
      (event) => {
        if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        const buttons = [...menu.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")];
        const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
        const next =
          event.key === "Home"
            ? 0
            : event.key === "End"
              ? buttons.length - 1
              : (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length;
        buttons[next]?.focus();
      },
      listen,
    );
  });
}

export function showBootError(root: HTMLElement): void {
  root.hidden = false;
  root.innerHTML = `<main class="welcome welcome-error"><section><h1>The house could not be reached.</h1><p>The game could not finish loading. Reload to try again.</p><button class="ui-button" type="button">Return to title</button></section></main>`;
  const button = root.querySelector("button")!;
  button.addEventListener("click", () => {
    const url = new URL(location.href);
    url.searchParams.delete("continue");
    location.assign(url);
  });
  button.focus();
}
