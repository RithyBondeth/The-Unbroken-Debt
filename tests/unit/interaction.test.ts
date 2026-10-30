import { afterEach, expect, it, vi } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { FreeCamera } from "@babylonjs/core/Cameras/freeCamera";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { MultiMaterial } from "@babylonjs/core/Materials/multiMaterial";
import { EventBus } from "../../src/core/EventBus";
import type { GameEvents } from "../../src/core/events";
import { Interaction } from "../../src/systems/interaction/Interaction";
import { InteractionHint } from "../../src/systems/interaction/InteractionHint";

const engines: NullEngine[] = [];
afterEach(() => {
  for (const engine of engines.splice(0)) engine.dispose();
  vi.unstubAllGlobals();
});

function setup(reducedMotion = false) {
  vi.stubGlobal("matchMedia", () => ({ matches: reducedMotion }));
  const engine = new NullEngine();
  engines.push(engine);
  vi.spyOn(engine, "getDeltaTime").mockReturnValue(20);
  const scene = new Scene(engine);
  const camera = new FreeCamera("eye", Vector3.Zero(), scene);
  camera.setTarget(Vector3.Forward());
  const bus = new EventBus<GameEvents>();
  const interaction = new Interaction(scene, camera, bus);
  const box = (name: string, x = 0, z = 1) => {
    const mesh = CreateBox(name, { size: 0.2 }, scene);
    mesh.position.set(x, 0, z);
    mesh.computeWorldMatrix(true);
    return mesh;
  };
  const settle = () => {
    for (let i = 0; i < 12; i++) interaction.update();
  };
  return { engine, scene, camera, bus, interaction, box, settle };
}

it("gives every registered object a contour and uses the same focused target", () => {
  const { interaction, box, bus, settle } = setup();
  const focus = vi.fn(),
    use = vi.fn();
  bus.on("interact:focus", focus);
  bus.on("interact:use", use);
  const drawer = box("drawer");
  interaction.add("drawer", drawer);
  interaction.update();
  const firstAlpha = drawer.edgesColor.a;
  settle();
  expect(interaction.focus).toBe("drawer");
  expect(drawer.edgesRenderer?.isEnabled).toBe(true);
  expect(firstAlpha).toBeGreaterThan(0);
  expect(drawer.edgesColor.a).toBeGreaterThan(firstAlpha);
  expect(drawer.edgesColor.a).toBeCloseTo(0.85);
  expect(focus).toHaveBeenCalledTimes(1);
  expect(interaction.use()).toBe("drawer");
  expect(use).toHaveBeenCalledWith({ id: "drawer" });
});

it("lets invisible pickup volumes focus visible geometry without outlining the volume", () => {
  const { scene, interaction, box, settle } = setup();
  const root = new TransformNode("lantern", scene);
  const volume = box("pickup");
  volume.visibility = 0;
  volume.parent = root;
  const body = box("body", 0.25);
  body.parent = root;
  interaction.add("lantern", root);
  settle();
  expect(interaction.focus).toBe("lantern");
  expect(body.edgesRenderer?.isEnabled).toBe(true);
  expect(volume.edgesRenderer).toBeNull();
});

it("keeps a whole shrine selectable while limiting its visual hint to the offering bowl", () => {
  const { scene, interaction, box, settle } = setup();
  const root = new TransformNode("shrine", scene);
  const carving = box("carved shrine");
  carving.parent = root;
  const bowl = box("offering bowl", 0.3);
  bowl.parent = root;
  interaction.add("shrine", root, [bowl]);
  settle();
  expect(interaction.focus).toBe("shrine");
  expect(interaction.use()).toBe("shrine");
  expect(carving.edgesRenderer).toBeNull();
  expect(bowl.edgesRenderer?.isEnabled).toBe(true);
  interaction.remove("shrine");
  expect(bowl.edgesRenderer?.isEnabled).toBe(false);
  expect(interaction.focus).toBeNull();
});

it("respects reach, walls, story gates and inactive menus", () => {
  const { interaction, box, settle } = setup();
  const item = box("item");
  interaction.add("item", item);
  settle();
  const wall = box("wall", 0, 0.5);
  settle();
  expect(interaction.focus).toBeNull();
  expect(item.edgesRenderer?.isEnabled).toBe(false);
  wall.dispose();
  interaction.allow = () => false;
  settle();
  expect(interaction.use()).toBeNull();
  interaction.allow = () => true;
  item.position.z = 3;
  item.computeWorldMatrix(true);
  settle();
  expect(interaction.focus).toBeNull();
  item.position.z = 1;
  item.computeWorldMatrix(true);
  settle();
  interaction.active = false;
  interaction.update();
  expect(item.edgesRenderer?.isEnabled).toBe(false);
  expect(interaction.use()).toBeNull();
});

it("clears collected or disabled geometry and fades the previous focus", () => {
  const { interaction, box, settle } = setup();
  const first = box("first");
  const second = box("second", 0.4);
  interaction.add("first", first);
  interaction.add("second", second);
  settle();
  first.position.x = -0.4;
  second.position.x = 0;
  first.computeWorldMatrix(true);
  second.computeWorldMatrix(true);
  interaction.update();
  expect(interaction.focus).toBe("second");
  expect(first.edgesColor.a).toBeLessThan(0.85);
  settle();
  expect(first.edgesRenderer?.isEnabled).toBe(false);
  second.setEnabled(false);
  interaction.update();
  expect(second.edgesRenderer?.isEnabled).toBe(false);
  second.setEnabled(true);
  settle();
  interaction.remove("second");
  expect(second.edgesRenderer?.isEnabled).toBe(false);
  expect(interaction.focus).toBeNull();
});

it("honours reduced motion and keeps the stroke consistent as distance changes", () => {
  const { interaction, box } = setup(true);
  const mesh = box("item");
  interaction.add("item", mesh);
  interaction.update();
  expect(mesh.edgesColor.a).toBeCloseTo(0.85);
  const width = mesh.edgesWidth;
  mesh.position.z = 1.5;
  mesh.computeWorldMatrix(true);
  interaction.update();
  expect(mesh.edgesWidth / width).toBeCloseTo(1.5);
});

it("installs the rim once per material and binds strength per mesh, including multi-materials", () => {
  const { scene, interaction, box, settle, engine } = setup();
  const shared = new PBRMaterial("shared wood", scene);
  const standard = new StandardMaterial("paper", scene);
  const multi = new MultiMaterial("combined", scene);
  multi.subMaterials = [shared, standard];
  const first = box("drawer");
  first.material = multi;
  const second = box("scenery", 0.5);
  second.material = shared;
  interaction.add("drawer", first);
  interaction.add("another", second);
  const rim = shared.pluginManager?.getPlugin("InteractionHint") as InteractionHint;
  expect(rim).toBeInstanceOf(InteractionHint);
  expect(standard.pluginManager?.getPlugin("InteractionHint")).toBeInstanceOf(InteractionHint);
  settle();
  const setFloat = vi.fn();
  for (const mesh of [first, second]) {
    rim.hardBindForSubMesh(undefined!, scene, engine, {
      effect: { setFloat },
      getRenderingMesh: () => mesh,
    } as never);
  }
  expect(setFloat.mock.calls).toEqual([
    ["interactionHint", 1],
    ["interactionHint", 0],
  ]);
  interaction.add("drawer", first);
  expect(shared.pluginManager?.getPlugin("InteractionHint")).toBe(rim);
});
