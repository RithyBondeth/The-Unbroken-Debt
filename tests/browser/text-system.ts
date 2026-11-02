/** Real UI components, isolated from graphics initialization and player saves. */
import {
  Hints,
  SaveIndicator,
  SatchelPanel,
  ScreenFade,
  Subtitles,
} from "../../src/ui/html/StoryUi";
import { setControlText } from "../../src/ui/html/controlText";
import { DocumentReader } from "../../src/ui/html/DocumentReader";
import { ARRIVAL_NOTE } from "../../src/episodes/ep1/data/arrival";
import { NotebookReader } from "../../src/ui/html/NotebookReader";
import { ResolutionView } from "../../src/episodes/ep1/resolution/ResolutionView";
import { ResolutionProgress } from "../../src/episodes/ep1/resolution/ResolutionProgress";
import { showWelcomeScreen, showBootError } from "../../src/ui/html/WelcomeScreen";
import { showRequirementsPage } from "../../src/ui/html/RequirementsPage";
import { renderStallNotice } from "../../src/ui/html/RenderStallNotice";
import { newGameSave } from "../../src/systems/saves/SaveData";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import { EventBus } from "../../src/core/EventBus";
import { notebookContent } from "../../src/ui/notebook/NotebookContent";
import type { Game } from "../../src/core/Game";
import type { SectionId } from "../../src/ui/diegetic/sketchbookContent";
import "../../src/ui/html/walker.css";

async function preview(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search);
  const view = params.get("view") ?? "hud";
  const controls = document.querySelector<HTMLElement>(".text-preview-controls")!;
  for (const [id, label] of Object.entries({
    hud: "Gameplay",
    stealth: "Stealth",
    title: "Story card",
    satchel: "Satchel",
    document: "Document",
    notebook: "Notebook",
    ending: "Ending",
    map: "Ending map",
    summary: "Ending summary",
    credits: "Credits",
    choice: "Story choice",
    caught: "Caught",
    entry: "Entry",
    menu: "Main menu",
    requirements: "Requirements",
    error: "Load error",
    stall: "Render warning",
  })) {
    const link = document.createElement("a");
    link.href = `?view=${id}`;
    link.textContent = label;
    if (id === view) link.setAttribute("aria-current", "page");
    controls.append(link);
  }
  controls.hidden = params.has("clean");
  const overlay = document.getElementById("overlay")!;
  switch (view) {
    case "title": {
      const fade = new ScreenFade();
      await fade.show({
        title: "The House of Mourning",
        khmer: "បុណ្យសព៖ បំណុលមិនដាច់",
        body: "Episode I",
        button: "Continue",
      });
      await fade.to(0, 0.65);
      break;
    }
    case "entry": {
      const fade = new ScreenFade();
      await fade.waitForEnter(() => {});
      await fade.to(0, 0.65);
      break;
    }
    case "satchel": {
      const satchel = new SatchelPanel();
      satchel.setAction({
        label: "Light the lamp · F",
        enabled: true,
        perform: () => satchel.close(),
      });
      satchel.open([
        { name: "Hurricane lamp", note: "The lamp is out." },
        { name: "Matches × 10", note: "Keep them dry." },
        { name: "Letters", note: "The letters from home." },
      ]);
      break;
    }
    case "document": {
      const arrival = params.get("note") === "arrival";
      const reader = new DocumentReader(
        arrival
          ? ARRIVAL_NOTE
          : [
              {
                title: "The fourth name",
                text: "Sok’s folded slip. Three names crossed out. A fourth scraped away until the paper is thin.",
              },
              {
                title: "The village pagoda",
                text: "Blood seeps across the map. The first faint mark darkens: the village pagoda.",
              },
            ],
        arrival ? "Mak Yey’s instructions" : undefined,
      );
      reader.show(0, () => {});
      break;
    }
    case "notebook": {
      const flags = new Flags();
      const inventory = new Inventory(new EventBus());
      const book = {
        isRaised: true,
        isVisible: true,
        section: "now" as SectionId,
        refreshContent() {},
        setPresentationHidden() {},
        showSection() {},
        goToSection(section: SectionId) {
          this.section = section;
        },
      };
      const reader = new NotebookReader({
        sketchbook: book,
        input: { clear() {} },
        gated: {},
        satchel: { close() {} },
        stopInspecting() {},
        closeSketchbook() {
          reader.back();
        },
        notebookContent: () =>
          notebookContent(
            flags,
            inventory,
            new Set(["SB-01"]),
            { x: 0, y: 0, z: 0 },
            "Studio · Drafting table",
          ),
      } as unknown as Game);
      reader.show();
      break;
    }
    case "ending":
    case "credits":
    case "map":
    case "summary":
    case "choice": {
      const resolution = new ResolutionView();
      if (view === "map") await resolution.map();
      else if (view === "credits")
        await resolution.credits(
          ["Episode 1 · The House of Mourning", "Created by Rithy Bondeth"],
          ["Episode summary", "Export completion save"],
        );
      else if (view === "summary") {
        const flags = new Flags();
        flags.set("lore.ep1.L1", true);
        await resolution.summary(new ResolutionProgress(flags));
      } else if (view === "choice")
        await resolution.show(
          "Sok’s journal",
          ["The journal is still in Sora’s hands. Vuthy waits beside the doorway."],
          ["Show Vuthy", "Keep the journal"],
        );
      else await resolution.slip();
      break;
    }
    case "caught": {
      const panel = document.createElement("div");
      panel.className = "walker-caught";
      const text = document.createElement("p");
      text.textContent = "The page tears.\nSomething moves beneath the house again.";
      panel.append(text);
      document.body.append(panel);
      break;
    }
    case "menu": {
      await showWelcomeScreen(overlay, {
        load: () =>
          Promise.resolve({ save: params.has("saved") ? newGameSave() : null, problem: null }),
      });
      break;
    }
    case "requirements": {
      showRequirementsPage(overlay, "no-webgpu");
      break;
    }
    case "error": {
      showBootError(overlay);
      break;
    }
    case "stall": {
      renderStallNotice.onStall?.(new Error("Preview of a recoverable rendering interruption."));
      break;
    }
    case "stealth": {
      const status = document.createElement("div");
      status.className = "road-stealth-status";
      status.setAttribute("role", "status");
      setControlText(
        status,
        "Footsteps at the gate. F puts out the lamp.\nStay beneath the pavilion. Hold C and let it pass.",
      );
      document.body.append(status);
      new Subtitles().show("Sora", "Those footsteps… Keep the lamp out. Let it pass.");
      break;
    }
    default: {
      const subtitles = new Subtitles();
      subtitles.show("Driver", "The rain has not stopped since we left the city.");
      new Hints().show("hint.sketchbook", 3600);
      new SaveIndicator().set(true);
    }
  }
}
void preview();
