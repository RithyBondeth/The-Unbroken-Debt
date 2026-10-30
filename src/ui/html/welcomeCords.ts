import { ALTAR, CORDS } from "./welcomeCordPaths";

export type CordPresence = "far" | "none" | "near";

export interface CordLayer {
  /** Swaps the cord render cut out around the Neak Ta; "near" makes every cord thrash. */
  setPresence(presence: CordPresence): void;
}

const LAYERS: Record<CordPresence, string> = {
  none: "assets/ui/welcome-cords.webp",
  far: "assets/ui/welcome-cords-far.webp",
  near: "assets/ui/welcome-cords-near.webp",
};

/**
 * Vertical offset of the cords at a frame position, in frame heights: a slow sway, a
 * fine tremble, and travelling waves while they thrash. The fragment shader evaluates
 * the same formula, so the blood beads stay on their cords.
 */
function offset(x: number, y: number, t: number, thrash: number): number {
  const reach = smooth(0.66, 0.5, y) * smooth(0.46, 0.56, x);
  const sway = Math.sin(0.7 * t + x * 4 + y * 2) * 2.4 + Math.sin(0.43 * t + x * 7.3) * 1.2;
  const tremble = Math.sin(x * 90 + t * 31) * Math.sin(x * 23 - t * 7) * 0.5;
  const wave = Math.sin(x * 28 - t * 40) * 7 * thrash;
  return ((sway + tremble + wave) / 1080) * reach;
}

function smooth(edge0: number, edge1: number, v: number): number {
  const k = Math.min(1, Math.max(0, (v - edge0) / (edge1 - edge0)));
  return k * k * (3 - 2 * k);
}

const VERTEX = `
attribute vec2 position;
varying vec2 uv;
void main() {
  uv = vec2(position.x * 0.5 + 0.5, 0.5 - position.y * 0.5);
  gl_Position = vec4(position, 0.0, 1.0);
}`;

const FRAGMENT = `
precision mediump float;
uniform sampler2D cords;
uniform float t;
uniform float thrash;
uniform vec2 altar;
varying vec2 uv;
void main() {
  float reach = smoothstep(0.66, 0.5, uv.y) * smoothstep(0.46, 0.56, uv.x);
  float sway = sin(0.7 * t + uv.x * 4.0 + uv.y * 2.0) * 2.4 + sin(0.43 * t + uv.x * 7.3) * 1.2;
  float tremble = sin(uv.x * 90.0 + t * 31.0) * sin(uv.x * 23.0 - t * 7.0) * 0.5;
  float wave = sin(uv.x * 28.0 - t * 40.0) * 7.0 * thrash;
  float dy = (sway + tremble + wave) / 1080.0 * reach;
  vec4 c = texture2D(cords, vec2(uv.x, uv.y - dy));
  // A slow pulse runs outward from the altar along the cords, like something feeding.
  float d = distance(uv * vec2(1.7778, 1.0), altar * vec2(1.7778, 1.0));
  float pulse = pow(0.5 + 0.5 * sin(d * 26.0 - t * 2.2), 14.0) * (0.55 + 0.6 * thrash);
  c.rgb += c.rgb * pulse * vec3(2.2, 0.5, 0.4);
  gl_FragColor = c;
}`;

interface Bead {
  cord: number;
  at: number;
  low: number;
  speed: number;
  hang: number;
  size: number;
  fall: number;
  velocity: number;
}

/**
 * Draws the red cords over the title plates and keeps them alive: they sway and
 * tremble, a pulse runs out from the altar, and blood beads slide to the low point of
 * each cord, swell and drip. Without WebGL, or with reduced motion, the stage's static
 * cord layer stays in place.
 */
export function animateCords(frame: HTMLElement, signal: AbortSignal): CordLayer {
  const base = import.meta.env.BASE_URL;
  const fallback: CordLayer = { setPresence() {} };
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return fallback;
  const canvas = document.createElement("canvas");
  const gl = canvas.getContext("webgl", { premultipliedAlpha: true, antialias: false });
  const beadCanvas = document.createElement("canvas");
  const ink = beadCanvas.getContext("2d");
  if (!gl || !ink) return fallback;
  canvas.className = "welcome-cords-live";
  beadCanvas.className = "welcome-cords-live";
  frame.querySelector(".welcome-cords")!.after(canvas, beadCanvas);

  const program = gl.createProgram();
  for (const [kind, source] of [
    [gl.VERTEX_SHADER, VERTEX],
    [gl.FRAGMENT_SHADER, FRAGMENT],
  ] as const) {
    const shader = gl.createShader(kind)!;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    gl.attachShader(program, shader);
  }
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    canvas.remove();
    beadCanvas.remove();
    return fallback;
  }
  gl.useProgram(program);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, "position");
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
  const uniform = (name: string) => gl.getUniformLocation(program, name);
  const uTime = uniform("t");
  const uThrash = uniform("thrash");
  gl.uniform2f(uniform("altar"), ALTAR[0], ALTAR[1]);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);

  const textures = new Map<CordPresence, WebGLTexture>();
  let presence: CordPresence = "far";
  for (const [key, path] of Object.entries(LAYERS) as [CordPresence, string][]) {
    const image = new Image();
    image.decoding = "async";
    image.src = base + path;
    void image.decode().then(
      () => {
        if (signal.aborted) return;
        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        textures.set(key, texture);
      },
      () => undefined,
    );
  }

  // Blood beads: each slides toward the lowest point of its cord, swells there and falls.
  const lows = CORDS.map((cord) =>
    cord.reduce((best, p, i) => (p[1] > cord[best][1] ? i : best), 0),
  );
  const visible = CORDS.map((cord) => cord.some(([x, y]) => x > 0.5 && y > 0.02 && y < 0.62));
  const spawn = (bead: Partial<Bead> = {}): Bead => {
    const options = CORDS.map((_, i) => i).filter((i) => visible[i]);
    const cord = options[Math.floor(Math.random() * options.length)];
    const low = lows[cord];
    const end = Math.random() < 0.5 ? 0 : CORDS[cord].length - 1;
    return {
      cord,
      low,
      at: end + (low - end) * Math.random() * 0.6,
      speed: 0.25 + Math.random() * 0.5,
      hang: 0,
      size: 0.7 + Math.random() * 0.5,
      fall: 0,
      velocity: 0,
      ...bead,
    };
  };
  const beads = Array.from({ length: 16 }, () => spawn());
  const pointOn = (cord: number, at: number): [number, number] => {
    const points = CORDS[cord];
    const i = Math.min(points.length - 2, Math.floor(at));
    const k = at - i;
    const [x0, y0] = points[i];
    const [x1, y1] = points[i + 1];
    return [x0 + (x1 - x0) * k, y0 + (y1 - y0) * k];
  };

  let width = 0;
  let height = 0;
  const resize = () => {
    const scale = Math.min(devicePixelRatio || 1, 1.5);
    width = Math.max(1, Math.round(frame.clientWidth * scale));
    height = Math.max(1, Math.round(frame.clientHeight * scale));
    canvas.width = beadCanvas.width = width;
    canvas.height = beadCanvas.height = height;
    gl.viewport(0, 0, width, height);
  };
  const observer = new ResizeObserver(resize);
  observer.observe(frame);
  resize();

  let thrash = 0;
  let last = performance.now();
  let raf = 0;
  const start = last;
  const draw = (now: number) => {
    raf = requestAnimationFrame(draw);
    const dt = Math.min(0.1, (now - last) / 1000);
    // About 30 fps is plenty for cords and spares laptop batteries.
    if (dt < 0.03) return;
    last = now;
    const t = (now - start) / 1000;
    thrash *= Math.exp(-dt / 0.9);
    const texture = textures.get(presence);
    if (!texture) return;
    frame.classList.add("welcome-cords-ready");
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.uniform1f(uTime, t);
    gl.uniform1f(uThrash, thrash);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    ink.clearRect(0, 0, width, height);
    for (const [index, bead] of beads.entries()) {
      if (bead.fall === 0) {
        const step = Math.sign(bead.low - bead.at) * bead.speed * dt * (1 + thrash * 6);
        if (Math.abs(bead.low - bead.at) > Math.abs(step)) bead.at += step;
        else {
          bead.at = bead.low;
          bead.hang += dt * (1 + thrash * 4);
          if (bead.hang > 2 + bead.size * 2) bead.fall = 0.0001;
        }
      } else {
        bead.velocity += dt * 0.9;
        bead.fall += bead.velocity * dt;
        if (bead.fall > 0.2) {
          beads[index] = spawn();
          continue;
        }
      }
      const [x, y] = pointOn(bead.cord, bead.at);
      const py = y + (bead.fall ? bead.fall : offset(x, y, t, thrash));
      const swell = 1 + Math.min(1, bead.hang / 2) * 0.8;
      const r = (height / 1080) * 1.5 * bead.size * (bead.fall ? 1.2 : swell);
      const alpha = bead.fall ? Math.max(0, 1 - bead.fall / 0.2) : 1;
      const cx = x * width;
      const cy = py * height + r * 0.8;
      ink.globalAlpha = 0.9 * alpha;
      ink.fillStyle = "#3d0604";
      ink.beginPath();
      ink.ellipse(cx, cy, r, r * (bead.fall ? 1.8 : 1.2), 0, 0, Math.PI * 2);
      ink.fill();
      ink.globalAlpha = 0.45 * alpha;
      ink.fillStyle = "#c2443a";
      ink.beginPath();
      ink.arc(cx - r * 0.3, cy - r * 0.35, r * 0.3, 0, Math.PI * 2);
      ink.fill();
    }
    ink.globalAlpha = 1;
  };
  raf = requestAnimationFrame(draw);

  const visibility = () => {
    cancelAnimationFrame(raf);
    if (!document.hidden) {
      last = performance.now();
      raf = requestAnimationFrame(draw);
    }
  };
  document.addEventListener("visibilitychange", visibility, { signal });
  signal.addEventListener("abort", () => {
    cancelAnimationFrame(raf);
    observer.disconnect();
    gl.getExtension("WEBGL_lose_context")?.loseContext();
  });

  return {
    setPresence(next) {
      if (next === "near") thrash = 1;
      else if (next !== presence) thrash = Math.max(thrash, 0.35);
      presence = next;
    },
  };
}
