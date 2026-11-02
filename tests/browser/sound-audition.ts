import { seededRandom } from "../../src/audio/synth";
import {
  pressureBed,
  ringingEars,
  sting,
  studioRoom,
} from "../../src/episodes/ep1/audio/dreadSounds";
import { taxiMotor, taxiWipers } from "../../src/episodes/ep1/audio/taxiSounds";
import { villageRain } from "../../src/episodes/ep1/audio/nightSounds";
import { thunder } from "../../src/episodes/ep1/audio/prologueSounds";
import {
  bambooKnock,
  carBuffet,
  crownRustle,
  frondClatter,
  gustSwell,
  leafHiss,
  trunkGroan,
  windRoar,
} from "../../src/episodes/ep1/audio/windSounds";

/** Plays each new or rebuilt Act 0 and Act 1 sound on its own, without loading the game. */
type Make = (rate: number) => Float32Array | Float32Array[];

const GROUPS: [string, [string, string, Make, boolean?][]][] = [
  [
    "Stingers",
    [
      ["Rise", "Clock stop, the figure by the taxi road", (r) => sting(r, "rise")],
      ["Shock", "The scream, the shrine, the cloth in the flash", (r) => sting(r, "shock")],
      ["Drop", "The line dying, a Neak Ta vanishing far off", (r) => sting(r, "drop")],
      ["Swell", "The watcher by the gate", (r) => sting(r, "swell")],
    ],
  ],
  [
    "Dread beds",
    [
      ["Pressure bed", "Rises under the silence and the Neak Ta", pressureBed, true],
      ["Ringing ears", "After the scream on the line", ringingEars],
    ],
  ],
  [
    "Act 0",
    [
      ["Studio room", "Room tone, the city, a cart and a dog", studioRoom, true],
      [
        "Taxi engine",
        "1930s four-cylinder, wet road, ruts",
        (r) => taxiMotor(r, seededRandom(210)),
        true,
      ],
      ["Taxi wipers", "Vacuum wipers on wet glass", (r) => taxiWipers(r, seededRandom(211)), true],
    ],
  ],
  [
    "Act 1",
    [
      [
        "Village rain (stereo)",
        "Now a take per ear instead of a point at the head",
        (r) => [villageRain(r, seededRandom(3)), villageRain(r, seededRandom(5))],
        true,
      ],
      ...[4, 8, 9].map(
        (seed, k) =>
          [
            `Thunder ${k + 1}`,
            "One of three rolls",
            (r: number) => thunder(r, seededRandom(seed)),
          ] as [string, string, Make],
      ),
    ],
  ],
  [
    "Wind (Episode 1)",
    [
      [
        "Wind roar (stereo)",
        "The air through the forest, under everything outdoors",
        (r) => [windRoar(r, seededRandom(7401)), windRoar(r, seededRandom(7402))],
        true,
      ],
      [
        "Leaf hiss (stereo)",
        "The canopy's wet leaves, risen and lowered with the gusts",
        (r) => [leafHiss(r, seededRandom(7403)), leafHiss(r, seededRandom(7404))],
        true,
      ],
      [
        "Gust swell",
        "One gust front passing, with its thin howl",
        (r) => gustSwell(r, seededRandom(7405)),
      ],
      [
        "Crown rustle",
        "One tree thrashing as a gust reaches it",
        (r) => crownRustle(r, seededRandom(7420)),
      ],
      [
        "Bamboo knock",
        "Culms knocking and squealing in the grove",
        (r) => bambooKnock(r, seededRandom(7422)),
      ],
      [
        "Frond clatter",
        "Palm fronds and banana leaves",
        (r) => frondClatter(r, seededRandom(7424)),
      ],
      [
        "Trunk groan",
        "A trunk taking a hard gust's weight",
        (r) => trunkGroan(r, seededRandom(7426)),
      ],
      ["Taxi buffet", "A gust striking the taxi's body", (r) => carBuffet(r, seededRandom(7409))],
    ],
  ],
];

let context: AudioContext | null = null;
let playing: AudioBufferSourceNode | null = null;
const cache = new Map<string, AudioBuffer>();
const status = document.getElementById("status")!;

function buffer(ctx: AudioContext, name: string, make: Make): AudioBuffer {
  const cached = cache.get(name);
  if (cached) return cached;
  const made = make(ctx.sampleRate);
  const channels = Array.isArray(made) ? made : [made];
  const out = ctx.createBuffer(channels.length, channels[0].length, ctx.sampleRate);
  channels.forEach((c, i) => out.copyToChannel(c as Float32Array<ArrayBuffer>, i));
  cache.set(name, out);
  return out;
}

const list = document.getElementById("list")!;
for (const [group, sounds] of GROUPS) {
  const heading = document.createElement("h2");
  heading.textContent = group;
  const ul = document.createElement("ul");
  for (const [name, note, make, loop] of sounds) {
    const li = document.createElement("li");
    const text = document.createElement("p");
    text.innerHTML = `<strong>${name}</strong>${note}${loop ? " · loops" : ""}`;
    const button = document.createElement("button");
    button.className = "ui-button";
    button.textContent = "Play";
    button.onclick = async () => {
      context ??= new AudioContext();
      await context.resume();
      playing?.stop();
      status.textContent = `Synthesising ${name}…`;
      await new Promise((r) => setTimeout(r, 20));
      const source = context.createBufferSource();
      source.buffer = buffer(context, name, make);
      source.loop = !!loop;
      source.connect(context.destination);
      source.start();
      playing = source;
      status.textContent = `Playing ${name}${loop ? " (looping, press Stop)" : ""}.`;
    };
    li.append(text, button);
    ul.append(li);
  }
  list.append(heading, ul);
}
const stop = document.createElement("button");
stop.className = "ui-button ui-button-primary";
stop.textContent = "Stop";
stop.onclick = () => {
  playing?.stop();
  playing = null;
  status.textContent = "Stopped.";
};
list.append(stop);
