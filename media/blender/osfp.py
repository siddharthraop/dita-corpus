"""Build and render an original, generic OSFP-style optical transceiver in Blender, headless.

    python media/blender/osfp.py --frames 72 --out /tmp/frames      # turntable frames
    python media/blender/osfp.py --still --out tpu/media/osfp-hero.png   # one high-quality still
    blender -b -P media/blender/osfp.py -- --still --out ...                 # same, with a Blender install

Needs Blender 4.2+ or the `bpy` module from PyPI (pip install bpy). Rendering uses Cycles on the
CPU, so it runs on a CI runner with no GPU. Proportions are illustrative, not taken from any
vendor's drawing. tools/render_media.sh turns the frames into the GIF and MP4 the topics embed.

The model is data-driven: change DIMS or FINS and re-run, and every image in the docs
regenerates in CI. That is the "visuals as code" half of docs as code.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy

# Proportions in Blender units (1 unit = 10 mm). Illustrative only.
DIMS = {"length": 10.8, "width": 2.26, "height": 1.3}
FINS = {"count": 11, "thickness": 0.06, "height": 0.42}
COLORS = {
    "shell": (0.62, 0.64, 0.67, 1.0),
    "fin": (0.70, 0.72, 0.75, 1.0),
    "port": (0.015, 0.015, 0.018, 1.0),
    "tab": (0.05, 0.36, 0.62, 1.0),
    "pcb": (0.04, 0.22, 0.10, 1.0),
    "gold": (0.95, 0.70, 0.30, 1.0),
    "label": (0.92, 0.92, 0.90, 1.0),
}


def args_after_dashes():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--frames", type=int, default=96)
    p.add_argument("--still", action="store_true")
    p.add_argument("--out", default="media/renders/frames")
    p.add_argument("--res", default=None, help="WIDTHxHEIGHT")
    p.add_argument("--samples", type=int, default=None)
    return p.parse_args(argv)


def material(name, color, metallic=0.0, roughness=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return m


def box(name, size, loc, mat, parent, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width, mod.segments = bevel, 3
    o.data.materials.append(mat)
    o.parent = parent
    bpy.ops.object.shade_smooth() if bevel else None
    return o


def cut(target, cutter):
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation, mod.object = "DIFFERENCE", cutter
    cutter.hide_render = True
    cutter.display_type = "WIRE"


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    L, W, H = DIMS["length"], DIMS["width"], DIMS["height"]
    mats = {
        "shell": material("shell", COLORS["shell"], 1.0, 0.32),
        "fin": material("fin", COLORS["fin"], 1.0, 0.28),
        "port": material("port", COLORS["port"], 0.0, 0.6),
        "tab": material("tab", COLORS["tab"], 0.0, 0.45),
        "pcb": material("pcb", COLORS["pcb"], 0.0, 0.5),
        "gold": material("gold", COLORS["gold"], 1.0, 0.25),
        "label": material("label", COLORS["label"], 0.0, 0.7),
    }
    bpy.ops.object.empty_add(location=(0, 0, 0))
    rig = bpy.context.active_object
    rig.name = "turntable"

    shell = box("shell", (L, W, H), (0, 0, H / 2), mats["shell"], rig, bevel=0.06)
    # Heat-sink fins run along the length, on top of the shell.
    n, t, fh = FINS["count"], FINS["thickness"], FINS["height"]
    span = W * 0.86
    for i in range(n):
        y = -span / 2 + i * span / (n - 1)
        box(f"fin.{i:02d}", (L * 0.78, t, fh), (-L * 0.06, y, H + fh / 2), mats["fin"], rig, bevel=0.01)
    # Optical port: two receptacles cut into the front face, with a dark interior.
    for i, y in enumerate((-W * 0.2, W * 0.2)):
        c = box(f"port-cut.{i}", (0.9, W * 0.3, H * 0.42), (L / 2, y, H * 0.48), mats["port"], rig)
        cut(shell, c)
        box(f"port-floor.{i}", (0.7, W * 0.28, H * 0.40), (L / 2 - 0.4, y, H * 0.48), mats["port"], rig)
    # Pull tab: a flat strip that leaves the front of the module, with a finger loop.
    box("tab", (2.6, W * 0.42, 0.06), (L / 2 + 1.2, 0, H * 0.12), mats["tab"], rig, bevel=0.02)
    loop = box("tab-loop", (0.9, W * 0.42, 0.5), (L / 2 + 2.5, 0, H * 0.12 + 0.2), mats["tab"], rig, bevel=0.15)
    hole = box("tab-hole", (0.55, W * 0.24, 1.0), (L / 2 + 2.5, 0, H * 0.12 + 0.2), mats["tab"], rig)
    cut(loop, hole)
    # Rear: the circuit-board edge with gold contacts.
    box("pcb", (0.9, W * 0.78, 0.12), (-L / 2 - 0.4, 0, H * 0.45), mats["pcb"], rig)
    pads = 16
    for i in range(pads):
        y = -W * 0.34 + i * (W * 0.68) / (pads - 1)
        box(f"pad.{i:02d}", (0.55, W * 0.025, 0.02), (-L / 2 - 0.55, y, H * 0.45 + 0.07), mats["gold"], rig)
    # Label panel on the side of the shell.
    box("label", (L * 0.32, 0.01, H * 0.5), (-L * 0.08, -W / 2 - 0.006, H * 0.5), mats["label"], rig)

    # Centre the whole assembly (shell, tab, board edge) on the turntable axis.
    for o in rig.children:
        o.location.x -= 1.05

    # Floor that only catches shadows, so the background stays clean.
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.is_shadow_catcher = True

    world = bpy.data.worlds.new("world")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.93, 0.94, 0.95, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9

    for name, loc, energy, size in (("key", (8, -9, 12), 1500, 6), ("fill", (-10, -4, 6), 550, 8), ("rim", (-4, 10, 9), 1200, 5)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.active_object
        light.name = name
        light.data.energy, light.data.size = energy, size
        direction = -light.location
        light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    bpy.ops.object.camera_add(location=(20.5, -17.5, 12.0))
    cam = bpy.context.active_object
    cam.data.lens = 50
    target = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(target)
    target.location = (0, 0, H * 0.45)
    track = cam.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    bpy.context.scene.camera = cam
    return rig


def configure(res, samples, transparent=False):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"


def main():
    a = args_after_dashes()
    rig = build()
    sc = bpy.context.scene
    if a.still:
        res = tuple(int(x) for x in (a.res or "1280x720").split("x"))
        configure(res, a.samples or 96)
        rig.rotation_euler = (0, 0, math.radians(-18))
        sc.render.filepath = str(Path(a.out).resolve())
        bpy.ops.render.render(write_still=True)
        return
    res = tuple(int(x) for x in (a.res or "640x360").split("x"))
    configure(res, a.samples or 24)
    sc.frame_start, sc.frame_end = 1, a.frames
    # Linear keys, 0 degrees at frame 1 and 360 at frame N+1, so frames 1..N loop with no seam.
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    rig.rotation_euler = (0, 0, 0)
    rig.keyframe_insert("rotation_euler", index=2, frame=1)
    rig.rotation_euler = (0, 0, math.radians(360))
    rig.keyframe_insert("rotation_euler", index=2, frame=a.frames + 1)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(out / "frame-")
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
