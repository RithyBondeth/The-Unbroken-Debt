import strings from "../../data/strings/en.json";
import type { RenderLoopOptions } from "../../render/renderLoop";

let notice: HTMLElement | null = null;

/**
 * Pass to runRenderLoop: while frames keep failing, say so over the canvas
 * instead of leaving a silent black screen, and take it away when they render
 * again. Development builds also show the error.
 */
export const renderStallNotice: RenderLoopOptions = {
  onStall(error) {
    if (!notice) {
      notice = document.createElement("section");
      notice.className = "render-stall";
      notice.setAttribute("role", "alert");
      document.body.appendChild(notice);
    }
    notice.innerHTML = `
      <h1>${strings["render.stall.title"]}</h1>
      <p>${strings["render.stall.body"]}</p>`;
    if (import.meta.env.DEV) {
      const detail = document.createElement("pre");
      detail.textContent = error instanceof Error ? error.message : String(error);
      notice.appendChild(detail);
    }
    notice.hidden = false;
  },
  onRecover() {
    if (notice) notice.hidden = true;
  },
};
