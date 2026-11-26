import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import {
  ALTAR,
  PARTITION,
  PICTURE,
  SHADOW,
  STUDIO_DOORS,
  altarDue,
  angleTo,
  balconyKnockDue,
  bathDoorDue,
  bathMirrorDue,
  bathTankDue,
  bedBreathDue,
  bookSlideDue,
  chairTurnDue,
  decodePoses,
  doorWatcherDue,
  dropBookDue,
  encodePoses,
  fanDriftDue,
  hallFlashDue,
  inBackRoom,
  inBathroom,
  phantomRingDue,
  pictureDue,
  runtime,
  shadowShot,
  stairStepsDue,
  studioHauntPhase,
  studioScareFlag,
  studioSpaceAt,
} from "@/episodes/ep1/data/studioScares";
import { Lightning } from "@/render/weather/Lightning";

/** Sora's eye at Blender (x, y), looking along Blender (dx, dy). */
const eyeAt = (x: number, y: number) => runtime(x, y, 1.58);
const looking = (dx: number, dy: number) => new Vector3(-dx, 0, -dy).normalize();
const NORTH = looking(0, 1);
const SOUTH = looking(0, -1);
/** The picture by the balcony doors on the east wall (Blender (4.58, 1.15, 1.75)). */
const PICTURE_AT = runtime(4.58, 1.15, 1.75);

describe("the picture", () => {
  it("falls behind Sora, not before she has been in the room a while", () => {
    // At the writing desk on the west wall, facing it: the picture is behind her.
    const eye = eyeAt(0.9, 2.5);
    const west = looking(-1, 0);
    expect(pictureDue(PICTURE.after - 1, eye, west, PICTURE_AT)).toBe(false);
    expect(pictureDue(PICTURE.after + 1, eye, west, PICTURE_AT)).toBe(true);
  });

  it("does not fall while she looks at it, stands under it or is out of the room", () => {
    expect(pictureDue(60, eyeAt(0.9, 2.5), looking(1, 0), PICTURE_AT)).toBe(false);
    expect(pictureDue(60, eyeAt(4.0, 1.3), looking(-1, 0), PICTURE_AT)).toBe(false);
    expect(pictureDue(60, eyeAt(2.0, 7.5), NORTH, PICTURE_AT)).toBe(false);
  });
});

describe("the shadow", () => {
  it("throws the figure's head beside Sora's view onto plain wall, the figure behind her", () => {
    // Walking up to the doorway (x 0.15-1.15), a metre from the partition.
    const eye = eyeAt(0.65, 5.0);
    const shot = shadowShot(30, eye, NORTH, 1.5);
    expect(shot).not.toBeNull();
    if (!shot) return;
    const wallX = -shot.wall.x;
    expect(wallX).toBeGreaterThanOrEqual(PARTITION.wall[0]);
    expect(wallX).toBeLessThanOrEqual(PARTITION.wall[1]);
    // Her head's shadow lands at about her own height, not down on the floor.
    expect(shot.wall.y).toBeGreaterThan(1.2);
    expect(shot.wall.y).toBeLessThan(1.6);
    // The figure stands just behind Sora, nearer the balcony doors.
    expect(-shot.feet.z).toBeCloseTo(5.0 - SHADOW.behindSora);
    expect(shot.feet.y).toBe(0);
    // The flash comes in at a balcony door: its light just inside the glass, in front of one.
    const light = shot.light;
    expect(-light.z).toBeGreaterThan(0);
    expect(-light.z).toBeLessThan(0.6);
    const atDoor = [
      [0.75, 1.65],
      [2.95, 3.85],
    ].some(([a, b]) => -light.x > a - 0.15 && -light.x < b + 0.15);
    expect(atDoor).toBe(true);
    // Her head is on the line from the light to that point on the wall.
    const head = shot.feet.add(new Vector3(0, 1.5, 0));
    const toWall = shot.wall.subtract(light).normalize();
    const toHead = head.subtract(light).normalize();
    expect(Vector3.Dot(toWall, toHead)).toBeCloseTo(1, 4);
  });

  it("works for any figure height and wherever Sora stands along the partition", () => {
    for (const head of [1.35, 1.5, 1.7])
      for (const x of [0.4, 1.0, 2.0, 3.0, 4.0])
        for (const y of [4.7, 5.0, 5.45])
          expect(shadowShot(30, eyeAt(x, y), NORTH, head)).not.toBeNull();
  });

  it("waits until Sora walks up to the partition facing it", () => {
    expect(shadowShot(30, eyeAt(0.65, 5.0), SOUTH)).toBeNull();
    expect(shadowShot(30, eyeAt(0.65, 2.5), NORTH)).toBeNull();
    expect(shadowShot(SHADOW.after - 1, eyeAt(0.65, 5.0), NORTH)).toBeNull();
    expect(shadowShot(30, eyeAt(0.65, 7.5), NORTH)).toBeNull();
  });
});

describe("the altar", () => {
  it("falls once Sora has had the satchel a moment and turned away, or waited", () => {
    expect(altarDue(ALTAR.settle - 0.1, 1, 180)).toBe(false);
    expect(altarDue(ALTAR.settle + 0.1, 1, 20)).toBe(false);
    expect(altarDue(ALTAR.settle + 0.1, 1, ALTAR.behind + 1)).toBe(true);
    expect(altarDue(ALTAR.settle + 0.1, ALTAR.patience, 0)).toBe(true);
    // Gone straight out of the room with the satchel: it falls anyway, in the end.
    expect(altarDue(ALTAR.settle + 0.1, 0, 0, ALTAR.offstage - 1)).toBe(false);
    expect(altarDue(ALTAR.settle + 0.1, 0, 0, ALTAR.offstage)).toBe(true);
    expect(inBackRoom(eyeAt(3.6, 12.0))).toBe(true);
    expect(inBackRoom(eyeAt(1.0, 8.0))).toBe(false);
  });

  it("measures how far round from her view something is, along the floor", () => {
    const eye = eyeAt(2, 2);
    expect(angleTo(eye, NORTH, eyeAt(2, 5))).toBeCloseTo(0);
    expect(angleTo(eye, NORTH, eyeAt(2, 0))).toBeCloseTo(180);
    expect(angleTo(eye, NORTH, eyeAt(4, 2))).toBeCloseTo(90);
  });
});

it("keeps where things fell as compact JSON and ignores anything broken", () => {
  const text = encodePoses({ picture: [1.23456, 0.01, -2, 0, 0.70710678, 0, 0.70710678] });
  expect(decodePoses(text)).toEqual({ picture: [1.235, 0.01, -2, 0, 0.7071, 0, 0.7071] });
  expect(decodePoses("")).toEqual({});
  expect(decodePoses("{not json")).toEqual({});
  expect(decodePoses(JSON.stringify({ a: [1, 2] }))).toEqual({});
  expect(studioScareFlag("altar")).toBe("ep1.scare.studio.altar");
});

it("lets a scare shape the next lightning flash", () => {
  const storm = new Lightning(() => 0.5);
  storm.update(0.016);
  storm.strike({ pulses: [0, 0.2], decay: 0.1 });
  const levels: number[] = [];
  for (let t = 0; t < 1.5; t += 0.01) levels.push(storm.update(0.01));
  // Lit at once, dimmer, lit again 0.2 s on, then dark and over.
  expect(levels[0]).toBeCloseTo(1, 1);
  expect(levels[15]).toBeLessThan(0.3);
  expect(levels[20]).toBeGreaterThan(0.8);
  expect(storm.flashing).toBe(false);
});

describe("4-phase studio haunt director and bathroom acoustics", () => {
  it("maps Sora's floor position to studio, back bedroom, and tiled bathroom acoustics", () => {
    expect(studioSpaceAt(eyeAt(2.3, 2.5))).toBe("studio");
    expect(studioSpaceAt(eyeAt(1.8, 11.5))).toBe("studioBack");
    expect(studioSpaceAt(eyeAt(1.7, 15.2))).toBe("bathroom");
    expect(inBathroom(eyeAt(1.7, 15.2))).toBe(true);
    expect(inBathroom(eyeAt(2.4, 13.5))).toBe(false);
  });

  it("escalates cleanly through phases 1 -> 2 -> 3 -> 4", () => {
    expect(
      studioHauntPhase({
        kitCount: 0,
        visitedBackOrBath: false,
        altarDone: false,
        phoneAnswered: false,
      }),
    ).toBe(1);
    expect(
      studioHauntPhase({
        kitCount: 1,
        visitedBackOrBath: true,
        altarDone: false,
        phoneAnswered: false,
      }),
    ).toBe(2);
    expect(
      studioHauntPhase({
        kitCount: 2,
        visitedBackOrBath: false,
        altarDone: false,
        phoneAnswered: false,
      }),
    ).toBe(2);
    expect(
      studioHauntPhase({
        kitCount: 2,
        visitedBackOrBath: true,
        altarDone: true,
        phoneAnswered: false,
      }),
    ).toBe(3);
    expect(
      studioHauntPhase({
        kitCount: 4,
        visitedBackOrBath: true,
        altarDone: true,
        phoneAnswered: true,
      }),
    ).toBe(4);
  });

  it("triggers Phase 1 ceiling fan drift and shelf book slide only off-camera in front studio", () => {
    const fan = runtime(2.3, 3.0, 2.75);
    const book = runtime(0.28, 4.4, 1.35);
    expect(fanDriftDue(8, eyeAt(1.0, 2.0), SOUTH, fan)).toBe(false);
    expect(fanDriftDue(12, eyeAt(1.0, 2.0), SOUTH, fan)).toBe(true);
    expect(fanDriftDue(12, eyeAt(1.0, 2.0), looking(1, 1), fan)).toBe(false);
    expect(bookSlideDue(18, eyeAt(2.5, 4.2), looking(1, 0), book)).toBe(true);
    expect(bookSlideDue(18, eyeAt(2.5, 4.2), looking(-1, 0), book)).toBe(false);
  });

  it("gates Phase 2 bathroom mirror, cistern ripple, and door creak haunts by gaze and room", () => {
    const mirror = runtime(1.72, 16.712, 1.57);
    const tank = runtime(0.5, 16.24, 0.72);
    const door = runtime(2.4, 14.15, 1.1);
    expect(bathMirrorDue(eyeAt(1.72, 15.2), NORTH, mirror)).toBe(true);
    expect(bathMirrorDue(eyeAt(1.72, 15.2), SOUTH, mirror)).toBe(false);
    expect(bathMirrorDue(eyeAt(1.72, 13.5), NORTH, mirror)).toBe(false);
    expect(bathTankDue(eyeAt(1.4, 15.3), looking(-1, 1), tank)).toBe(true);
    expect(bathTankDue(eyeAt(1.4, 15.3), looking(1, -1), tank)).toBe(false);
    expect(bathDoorDue(eyeAt(1.7, 15.6), NORTH, door, false)).toBe(false);
    expect(bathDoorDue(eyeAt(1.7, 15.6), NORTH, door, true)).toBe(true);
    expect(bathDoorDue(eyeAt(1.7, 15.6), SOUTH, door, true)).toBe(false);
  });

  it("gates Phase 4 doorframe watcher and stair-gate steps after Yay Mey's phone call", () => {
    const watcher = runtime(1.06, 9.42, 1.45);
    const stair = runtime(3.6, 6.2, 1.0);
    expect(doorWatcherDue(eyeAt(1.1, 6.5), NORTH, watcher, false)).toBe(false);
    expect(doorWatcherDue(eyeAt(1.1, 6.5), NORTH, watcher, true)).toBe(true);
    expect(doorWatcherDue(eyeAt(1.1, 6.5), SOUTH, watcher, true)).toBe(false);
    expect(stairStepsDue(eyeAt(3.1, 6.6), stair, true, false)).toBe(false);
    expect(stairStepsDue(eyeAt(3.1, 6.6), stair, true, true)).toBe(true);
  });

  it("gates the expanded surprise haunts (balcony knock, phantom ring, bed breath, stool turn, book drop, hall flash)", () => {
    const balcony = runtime(1.3, 0.0, 1.5);
    expect(balconyKnockDue(20, eyeAt(2.2, 3.0), NORTH, balcony)).toBe(false);
    expect(balconyKnockDue(30, eyeAt(2.2, 3.0), NORTH, balcony)).toBe(true);
    expect(balconyKnockDue(30, eyeAt(2.2, 3.0), SOUTH, balcony)).toBe(false);

    expect(phantomRingDue(25, eyeAt(2.2, 11.0), true, false)).toBe(false);
    expect(phantomRingDue(35, eyeAt(2.2, 11.0), false, false)).toBe(false);
    expect(phantomRingDue(35, eyeAt(2.2, 11.0), true, true)).toBe(false);
    expect(phantomRingDue(35, eyeAt(2.2, 11.0), true, false)).toBe(true);

    const bed = runtime(3.8, 12.6, 0.35);
    expect(bedBreathDue(eyeAt(2.6, 12.2), bed, false)).toBe(true);
    expect(bedBreathDue(eyeAt(2.6, 12.2), bed, true)).toBe(false);
    expect(bedBreathDue(eyeAt(1.7, 15.2), bed, false)).toBe(false);

    const stool = runtime(3.05, 2.55, 0.3);
    expect(chairTurnDue(25, eyeAt(1.5, 2.5), looking(-1, 0), stool, false)).toBe(false);
    expect(chairTurnDue(25, eyeAt(1.5, 2.5), looking(-1, 0), stool, true)).toBe(true);
    expect(chairTurnDue(25, eyeAt(1.5, 2.5), looking(1, 0), stool, true)).toBe(false);

    const dropBook = runtime(0.3, 5.1, 1.65);
    expect(dropBookDue(32, eyeAt(2.6, 4.5), looking(1, 0), dropBook, true)).toBe(true);
    expect(dropBookDue(32, eyeAt(2.6, 4.5), looking(-1, 0), dropBook, true)).toBe(false);

    const backDoor = runtime(0.65, 9.18, 1.45);
    expect(hallFlashDue(eyeAt(1.0, 6.8), NORTH, backDoor, false)).toBe(false);
    expect(hallFlashDue(eyeAt(1.0, 6.8), NORTH, backDoor, true)).toBe(true);
    expect(hallFlashDue(eyeAt(1.0, 6.8), SOUTH, backDoor, true)).toBe(false);
  });

  it("configures all four interactive studio doors with valid open, closed, and ajar poses", () => {
    expect(Object.keys(STUDIO_DOORS).sort()).toEqual([
      "haunt_balcony_door",
      "haunt_bath_door",
      "haunt_bedroom_door",
      "haunt_partition_door",
    ]);
    expect(STUDIO_DOORS.haunt_partition_door.openDeg).toBe(88);
    expect(STUDIO_DOORS.haunt_bedroom_door.openDeg).toBe(88);
    expect(STUDIO_DOORS.haunt_bath_door.openDeg).toBe(132);
    expect(STUDIO_DOORS.haunt_balcony_door.initialDeg).toBe(0);
    expect(STUDIO_DOORS.haunt_balcony_door.openDeg).toBeLessThan(0);
  });
});
