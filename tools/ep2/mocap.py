"""Real human motion for Episode 2's ghosts: BVH clips from the CMU Motion Capture Database
(mocap.cs.cmu.edu, Bruce Hahne's BVH conversion; free for commercial use), retargeted onto
each ghost's own skeleton as Blender actions.

Each target bone takes the world rotation of its source joint, corrected by the one
rotation that turns the target's rest direction onto the source's. So a ghost keeps its
own proportions and rest pose, and gets the performer's arcs, weight and timing.
"""
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
MOCAP = ROOT / 'art-source/library/mocap'
# BVH is Y up with the performer facing +Z; Blender here is Z up, facing -Y.
AXES = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
AXES_INV = AXES.transposed()


class Joint:
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.offset = Vector((0, 0, 0))
        self.channels = []
        self.first = 0
        self.children = []
        self.end = None  # End Site offset, for joints with no child


def parse(path):
    """Reads a BVH file: returns (joints by name, in order), frames array, frame time."""
    tokens = Path(path).read_text().split()
    i = 0
    joints = {}
    stack = []
    channel = 0

    while tokens[i] != 'MOTION':
        t = tokens[i]
        if t in ('ROOT', 'JOINT'):
            j = Joint(tokens[i + 1], stack[-1] if stack else None)
            joints[j.name] = j
            if j.parent:
                j.parent.children.append(j)
            stack.append(j)
            i += 2
        elif t == 'End':
            i += 2
            assert tokens[i] == '{'
            assert tokens[i + 1] == 'OFFSET'
            stack[-1].end = Vector(float(x) for x in tokens[i + 2:i + 5])
            assert tokens[i + 5] == '}'
            i += 6
        elif t == 'OFFSET':
            stack[-1].offset = Vector(float(x) for x in tokens[i + 1:i + 4])
            i += 4
        elif t == 'CHANNELS':
            n = int(tokens[i + 1])
            stack[-1].channels = tokens[i + 2:i + 2 + n]
            stack[-1].first = channel
            channel += n
            i += 2 + n
        elif t == '}':
            stack.pop()
            i += 1
        else:
            i += 1
    # MOTION / Frames: n / Frame Time: t
    frames = int(tokens[i + 2])
    dt = float(tokens[i + 5])
    data = np.array(tokens[i + 6:i + 6 + frames * channel], dtype=np.float64).reshape(frames, channel)
    return joints, data, dt


def _axis_rot(axis, deg):
    return Quaternion({'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[axis], math.radians(deg))


class Clip:
    """A stretch of a BVH file, resampled, as world rotations and root positions, all in
    Blender axes. Rotations are relative to the performer's T-pose."""

    def __init__(self, name, start=0.0, end=None, fps=30):
        self.joints, data, dt = parse(MOCAP / f'{name}.bvh')
        step = 1 / (fps * dt)
        last = len(data) - 1 if end is None else min(len(data) - 1, int(end / dt))
        rows = np.arange(start / dt, last, step).astype(int)
        self.fps = fps
        self.count = len(rows)
        conj = AXES.to_quaternion()
        self.world = {n: [None] * len(rows) for n in self.joints}
        self.root = []
        order = list(self.joints.values())
        root = order[0]
        for f, r in enumerate(rows):
            row = data[r]
            for j in order:
                q = Quaternion()
                pos = None
                for c, name_ in enumerate(j.channels):
                    v = row[j.first + c]
                    if name_.endswith('rotation'):
                        q = q @ _axis_rot(name_[0], v)
                    elif j is root:
                        pos = pos or {}
                        pos[name_[0]] = v
                parent = self.world[j.parent.name][f] if j.parent else conj
                self.world[j.name][f] = parent @ q if j.parent else conj @ q
                if j is root:
                    self.root.append(AXES @ Vector((pos['X'], pos['Y'], pos['Z'])))
        # Rotations above were built in world axes by conjugating at the root only:
        # strip the trailing BVH-axes frame so each is a rotation in Blender axes.
        for n in self.world:
            self.world[n] = [q @ conj.inverted() for q in self.world[n]]
        self.root = np.array(self.root)
        # Rest geometry in Blender axes.
        self.rest = {}
        for j in order:
            self.rest[j.name] = AXES @ j.offset
        self.ends = {j.name: AXES @ j.end for j in order if j.end is not None}

    def reverse(self):
        """Plays the performance backwards: kneeling down becomes getting up."""
        for n in self.world:
            self.world[n] = self.world[n][::-1]
        self.root = self.root[::-1].copy()
        return self

    def direction(self, name):
        """Rest-pose direction of a joint's bone, towards its (first useful) child."""
        j = self.joints[name]
        for c in j.children:
            if self.rest[c.name].length > 1e-3:
                return self.rest[c.name].normalized()
        if name in self.ends and self.ends[name].length > 1e-3:
            return self.ends[name].normalized()
        return None

    def height(self, up='LeftUpLeg', chain=('LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase')):
        """How far the hips stand above the floor in the performer's rest pose."""
        return -sum(self.rest[n].z for n in chain) if chain else 0.0

    def stride_speed(self):
        """Mean ground speed of the root, in the source's units per second."""
        d = np.diff(self.root[:, :2], axis=0)
        return float(np.linalg.norm(d, axis=1).sum() / (self.count / self.fps))


def clean_walk(clip, window=1.2):
    """Removes the performer's travel and turning from a walk, leaving only the body's own
    bob, sway and twist, facing -Y: the game moves the root along its own path."""
    n = clip.count
    w = max(3, int(window * clip.fps))
    pad = np.pad(clip.root[:, :2], ((w, w), (0, 0)), mode='edge')
    kernel = np.ones(w) / w
    path = np.stack([np.convolve(pad[:, k], kernel, mode='same')[w:-w] for k in (0, 1)], 1)
    v = np.gradient(path, axis=0)
    yaw = np.arctan2(v[:, 0], -v[:, 1])  # 0 when travelling along -Y
    yaw = np.unwrap(yaw)
    for f in range(n):
        turn = Quaternion((0, 0, 1), -yaw[f])  # undoes the heading
        for name in clip.world:
            clip.world[name][f] = turn @ clip.world[name][f]
        rel = Vector((clip.root[f, 0] - path[f, 0], clip.root[f, 1] - path[f, 1], 0))
        rel.rotate(turn)
        clip.root[f, 0], clip.root[f, 1] = rel.x, rel.y
    return clip


def clean_stand(clip):
    """For a performer standing about: faces them along -Y on average and centres them."""
    hips = clip.world['Hips']
    forward = sum((q @ Vector((0, -1, 0)) for q in hips), Vector())
    turn = Quaternion((0, 0, 1), -math.atan2(forward.x, -forward.y))
    centre = clip.root[:, :2].mean(0)
    for f in range(clip.count):
        for name in clip.world:
            clip.world[name][f] = turn @ clip.world[name][f]
        rel = Vector((clip.root[f, 0] - centre[0], clip.root[f, 1] - centre[1], 0))
        rel.rotate(turn)
        clip.root[f, 0], clip.root[f, 1] = rel.x, rel.y
    return clip


def make_loop(clip, length, blend=.3):
    """Cuts one cycle of about `length` seconds: finds where the pose comes back round
    best, then eases the end into the start so it repeats without a hitch."""
    fps = clip.fps
    keys = ['LeftUpLeg', 'RightUpLeg', 'LeftLeg', 'RightLeg', 'LeftArm', 'RightArm']

    def pose(f):
        return np.concatenate([np.array(clip.world[k][f]) for k in keys])
    target = int(length * fps)
    best = None
    margin = int(.8 * fps)
    for a in range(margin, max(margin + 1, clip.count - target - margin), 2):
        for L in range(int(target * .8), int(target * 1.2) + 1, 2):
            if a + L >= clip.count:
                continue
            d = np.linalg.norm(pose(a) - pose(a + L))
            if best is None or d < best[0]:
                best = (d, a, L)
    _, a, L = best
    blend_frames = int(blend * fps)
    for name in clip.world:
        seq = clip.world[name]
        out = seq[a:a + L]
        for k in range(blend_frames):
            t = (k + 1) / (blend_frames + 1)
            t = t * t * (3 - 2 * t)
            i = L - blend_frames + k
            out[i] = out[i].slerp(seq[a - blend_frames + k], t)
        clip.world[name] = out
    roots = clip.root[a:a + L].copy()
    for k in range(blend_frames):
        t = (k + 1) / (blend_frames + 1)
        t = t * t * (3 - 2 * t)
        i = L - blend_frames + k
        roots[i] = roots[i] * (1 - t) + clip.root[a - blend_frames + k] * t
    clip.root = roots
    clip.count = L
    return clip


def limp_arms(rig, rests):
    """An `extra` for retarget: bones in `rests` ({bone: direction in armature space}) take
    that direction against their parent instead of holding their rest pose, with a slow
    slight sway. Used with bones left out of the mapping: dead arms that just hang."""
    arm = rig.data
    turns = {}
    rest = {}
    for name, direction in rests.items():
        b = arm.bones[name]
        along = (Vector(b.tail_local) - Vector(b.head_local)).normalized()
        turns[name] = along.rotation_difference(Vector(direction).normalized())
        rest[name] = b.matrix_local.to_quaternion()
        if b.parent and b.parent.name in rests:
            # Measured from where its parent will already have taken it.
            turns[name] = turns[b.parent.name].inverted() @ turns[name]

    def extra(name, frame, q):
        turn = turns.get(name)
        if turn is None:
            return q
        sway = Quaternion((1, 0, 0), math.radians(1.6) * math.sin(frame * .05 + hash(name) % 7))
        return q @ rest[name].inverted() @ (turn @ sway) @ rest[name]
    return extra


def assign(rig, action):
    """Makes `action` the rig's current action (Blender 5's actions have slots)."""
    rig.animation_data_create()
    rig.animation_data.action = action
    if len(action.slots):
        rig.animation_data.action_slot = action.slots[0]


def retarget(clip, rig, mapping, name, root_bone, hips_height, scale=None, travel=True, feet=None, extra=None):
    """Keys `clip` onto armature `rig` as a new action called `name`.

    `mapping` is {target bone: source joint, or (joint a, joint b, t) to blend two}; bones
    left out keep their rest pose against their parent. `extra(bone, frame, q)` may change
    a bone's world rotation. `feet` names the bones that must meet the floor."""
    bones = rig.pose.bones
    arm = rig.data
    scale = scale if scale is not None else hips_height / clip.height()
    action = bpy.data.actions.new(name)
    assign(rig, action)
    rest_world = {b.name: b.bone.matrix_local.to_quaternion() for b in bones}
    # Target and source agree on direction at rest through this one correction per bone.
    align = {}
    for b in bones:
        src = mapping.get(b.name)
        if isinstance(src, str):
            d = clip.direction(src)
            if d is not None:
                tgt = (Vector(arm.bones[b.name].tail_local) - Vector(arm.bones[b.name].head_local)).normalized()
                align[b.name] = tgt.rotation_difference(d)
    order = [b for b in bones if not b.parent] + [b for b in bones if b.parent]
    # Parents before children.
    seen, ordered = set(), []

    def visit(b):
        if b.name in seen:
            return
        if b.parent:
            visit(b.parent)
        seen.add(b.name)
        ordered.append(b)
    for b in order:
        visit(b)
    start = Vector(clip.root[0]) * scale
    moves = []
    for b in ordered:
        b.rotation_mode = 'QUATERNION'
    root_rest = Vector(arm.bones[root_bone].head_local)
    for f in range(clip.count):
        world = {}
        for b in ordered:
            src = mapping.get(b.name)
            if src is None:
                # Follows its parent, as at rest.
                parent = world.get(b.parent.name) if b.parent else Quaternion()
                world[b.name] = parent @ rest_world[b.parent.name].inverted() @ rest_world[b.name] if b.parent else rest_world[b.name]
                if extra:
                    world[b.name] = extra(b.name, f, world[b.name])
            else:
                if isinstance(src, str):
                    q = clip.world[src][f]
                else:
                    q = clip.world[src[0]][f].slerp(clip.world[src[1]][f], src[2])
                a = align.get(b.name, Quaternion())
                w = q @ a @ rest_world[b.name]
                if extra:
                    w = extra(b.name, f, w)
                world[b.name] = w
            if b.parent:
                rel = rest_world[b.name].inverted() @ rest_world[b.parent.name] @ world[b.parent.name].inverted() @ world[b.name]
            else:
                rel = rest_world[b.name].inverted() @ world[b.name]
            # Keep the shortest way round between keys.
            if f and b.rotation_quaternion.dot(rel) < 0:
                rel = -rel
            b.rotation_quaternion = rel
            b.keyframe_insert('rotation_quaternion', frame=f + 1)
        # The root travels: its offset in armature space, turned into the bone's frame.
        p = Vector(clip.root[f]) * scale
        if travel:
            moves.append(p - Vector((start.x, start.y, 0)))
        else:
            moves.append(p.copy())
    # The feet find the floor: the whole clip shifts so its lowest step just touches it.
    assign(rig, action)
    feet = [n for n in (feet or ()) if n in bones]
    rest_low = min(Vector(arm.bones[n].head_local).z for n in feet) if feet else 0
    rb = bones[root_bone]

    def key_root(lift):
        for f, move in enumerate(moves):
            delta = Vector((move.x, move.y, move.z + lift - root_rest.z))
            rb.location = rest_world[root_bone].inverted() @ delta
            rb.keyframe_insert('location', frame=f + 1)
    key_root(0)
    if feet:
        scene = bpy.context.scene
        low = 1e9
        for f in range(1, clip.count + 1, 2):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            low = min(low, min(bones[n].head.z for n in feet))
        key_root(rest_low - low)
    action.use_fake_user = True
    rig.animation_data.action = None
    return action
