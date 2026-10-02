"""Build Dub Assistant.maxpat and an unfrozen MIDI-effect .amxd."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "device"
USER_LIB = Path(
    r"./output Library\Presets\MIDI Effects\Max MIDI Effect\Dub Assistant"
)

W = 820.0
H = 268.0
TRACKS = [
    "Drums",
    "Bass",
    "Vox",
    "Keys",
    "Guitar",
    "FX",
    "Perc",
    "Other",
]


def box_base(oid: str, maxclass: str, x: float, y: float, w: float, h: float) -> dict:
    return {
        "id": oid,
        "maxclass": maxclass,
        "patching_rect": [x, y + 360.0, w, h],
        "presentation": 1,
        "presentation_rect": [x, y, w, h],
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": [""],
        "parameter_enable": 0,
    }


def comment(oid: str, text: str, x: float, y: float, w: float, h: float = 16.0, size: float = 10.0) -> dict:
    b = box_base(oid, "comment", x, y, w, h)
    b["text"] = text
    b["fontsize"] = size
    b["fontname"] = "Ableton Sans Medium"
    b["textcolor"] = [0.82, 0.82, 0.82, 1.0]
    b["numinlets"] = 1
    b["numoutlets"] = 0
    b["outlettype"] = []
    return {"box": b}


def live_dial(
    oid: str,
    longname: str,
    shortname: str,
    x: float,
    y: float,
    default: float = 0.5,
    unit: int = 1,
) -> dict:
    b = box_base(oid, "live.dial", x, y, 48.0, 52.0)
    b["numinlets"] = 1
    b["numoutlets"] = 2
    b["outlettype"] = ["", "float"]
    b["parameter_enable"] = 1
    b["varname"] = longname
    b["saved_attribute_attributes"] = {
        "valueof": {
            "parameter_longname": longname,
            "parameter_shortname": shortname,
            "parameter_type": 0,
            "parameter_unitstyle": unit,
            "parameter_mmin": 0.0,
            "parameter_mmax": 1.0,
            "parameter_initial": [default],
            "parameter_modmode": 0,
        }
    }
    return {"box": b}


def live_num(
    oid: str,
    longname: str,
    shortname: str,
    x: float,
    y: float,
    default: float = 0.4,
) -> dict:
    b = box_base(oid, "live.numbox", x, y, 36.0, 16.0)
    b["numinlets"] = 1
    b["numoutlets"] = 2
    b["outlettype"] = ["", "float"]
    b["parameter_enable"] = 1
    b["varname"] = longname
    b["fontsize"] = 9.0
    b["saved_attribute_attributes"] = {
        "valueof": {
            "parameter_longname": longname,
            "parameter_shortname": shortname,
            "parameter_type": 0,
            "parameter_unitstyle": 1,
            "parameter_mmin": 0.0,
            "parameter_mmax": 1.0,
            "parameter_initial": [default],
            "parameter_modmode": 0,
        }
    }
    return {"box": b}


def live_slider(oid: str, longname: str, x: float, y: float) -> dict:
    b = box_base(oid, "live.slider", x, y, 18.0, 52.0)
    b["numinlets"] = 1
    b["numoutlets"] = 2
    b["outlettype"] = ["", "float"]
    b["parameter_enable"] = 1
    b["orientation"] = 1
    b["varname"] = longname
    b["saved_attribute_attributes"] = {
        "valueof": {
            "parameter_longname": longname,
            "parameter_shortname": longname,
            "parameter_type": 0,
            "parameter_unitstyle": 1,
            "parameter_mmin": 0.0,
            "parameter_mmax": 1.0,
            "parameter_initial": [0.85],
            "parameter_modmode": 0,
            "parameter_invisible": 1,
        }
    }
    return {"box": b}


def live_text(oid: str, label: str, x: float, y: float, w: float = 72.0) -> dict:
    b = box_base(oid, "live.text", x, y, w, 18.0)
    b["text"] = label
    b["texton"] = label
    b["mode"] = 0
    b["fontsize"] = 10.0
    b["numinlets"] = 1
    b["numoutlets"] = 2
    b["outlettype"] = ["", ""]
    b["parameter_enable"] = 0
    b["varname"] = label
    return {"box": b}


def newobj(oid: str, text: str, x: float, y: float, w: float = 140.0, outlets: int = 1) -> dict:
    types = [""] * outlets
    b = {
        "id": oid,
        "maxclass": "newobj",
        "text": text,
        "patching_rect": [x, y, w, 22.0],
        "numinlets": 1,
        "numoutlets": outlets,
        "outlettype": types,
        "fontsize": 10.0,
        "fontname": "Ableton Sans Medium",
    }
    return {"box": b}


def message(oid: str, text: str, x: float, y: float, w: float = 80.0) -> dict:
    b = {
        "id": oid,
        "maxclass": "message",
        "text": text,
        "patching_rect": [x, y, w, 22.0],
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "fontsize": 10.0,
    }
    return {"box": b}


def comment_hidden(oid: str, text: str, x: float, y: float) -> dict:
    return {
        "box": {
            "id": oid,
            "maxclass": "comment",
            "text": text,
            "patching_rect": [x, y, 420.0, 32.0],
            "fontsize": 11.0,
            "numinlets": 1,
            "numoutlets": 0,
            "outlettype": [],
            "presentation": 0,
        }
    }


def line(src: str, src_outlet: int, dst: str, dst_inlet: int = 0) -> dict:
    return {
        "patchline": {
            "source": [src, src_outlet],
            "destination": [dst, dst_inlet],
        }
    }


def build_patcher() -> dict:
    boxes: list[dict] = []
    lines: list[dict] = []

    boxes.append(comment("c-title", "Dub Assistant", 8, 4, 140, 18, 13))

    buttons = [
        ("btn-learn", "Learn this!", 8, 28, 84),
        ("btn-train", "Train", 96, 28, 52),
        ("btn-bind", "Bind", 152, 28, 48),
        ("btn-save", "Save", 204, 28, 48),
        ("btn-load", "Load", 256, 28, 48),
        ("btn-clear", "Clear", 308, 28, 48),
        ("btn-q4", "1/4", 700, 28, 40),
        ("btn-q8", "1/8", 744, 28, 40),
    ]
    for oid, label, x, y, w in buttons:
        boxes.append(live_text(oid, label, x, y, w))

    boxes.append(comment("c-rows", "rows 0", 364, 30, 80, 14, 10))
    boxes.append(comment("c-div", "faders 1/8", 460, 30, 90, 14, 10))

    perf = [
        ("dial-col", "Colour", "col", 12, 58, 0.5),
        ("dial-rhy", "Rhythm", "rhy", 64, 58, 0.5),
        ("dial-dyn", "Dynamics", "dyn", 116, 58, 0.5),
        ("dial-heart", "Heart", "heart", 700, 58, 1.0),
        ("dial-wet", "Dry/Wet", "drywet", 752, 58, 0.0),
    ]
    for oid, longname, short, x, y, default in perf:
        boxes.append(live_dial(oid, longname, short, x, y, default, 1))

    boxes.append(comment("c-col", "col", 22, 110, 32, 12, 9))
    boxes.append(comment("c-rhy", "rhy", 74, 110, 32, 12, 9))
    boxes.append(comment("c-dyn", "dyn", 126, 110, 32, 12, 9))
    boxes.append(comment("c-heart", "heart", 704, 110, 40, 12, 9))
    boxes.append(comment("c-wet", "dry/wet", 752, 110, 50, 12, 9))
    boxes.append(comment("c-sends", "sends  (return A)", 188, 52, 140, 12, 9))
    boxes.append(comment("c-faders", "predicted sends", 188, 124, 120, 12, 9))
    boxes.append(comment("c-prob", "slider probability", 188, 192, 140, 12, 9))
    boxes.append(comment("c-dynam", "slider dynamics", 188, 226, 140, 12, 9))

    for i, name in enumerate(TRACKS):
        sx = 188.0 + i * 58.0
        boxes.append(live_dial(f"dial-s{i}", f"Send {name}", f"s{i+1}", sx, 64, 0.0, 1))
        boxes.append(comment(f"c-tn{i}", name, sx + 4, 116, 50, 12, 9))
        boxes.append(live_slider(f"sl-f{i}", f"Fader {name}", sx + 14, 136))
        boxes.append(live_num(f"nb-p{i}", f"Prob {name}", f"p{i+1}", sx + 6, 206, 0.35))
        boxes.append(live_num(f"nb-d{i}", f"Dyn {name}", f"d{i+1}", sx + 6, 240, 0.40))

    # Hidden patcher objects (below presentation)
    boxes.append(comment_hidden(
        "c-help",
        "Dub Assistant — Max MIDI Effect. Keep dub-assistant.js next to this device. "
        "live.thisdevice bangs init. Do not use LiveAPI in loadbang.",
        20,
        20,
    ))
    boxes.append(newobj("obj-this", "live.thisdevice", 20, 70, 110, 2))
    boxes.append(
        {
            "box": {
                "id": "obj-js",
                "maxclass": "newobj",
                "text": "js dub-assistant.js",
                "patching_rect": [20, 110, 170, 22],
                "numinlets": 1,
                "numoutlets": 3,
                "outlettype": ["", "", "int"],
                "fontsize": 10.0,
                "saved_object_attributes": {
                    "filename": "dub-assistant.js",
                    "parameter_enable": 0,
                    "autowatch": 1,
                },
            }
        }
    )
    boxes.append(
        {
            "box": {
                "id": "obj-status",
                "maxclass": "textedit",
                "patching_rect": [210, 110, 360, 22],
                "presentation": 1,
                "presentation_rect": [160, 6, 500, 16],
                "numinlets": 1,
                "numoutlets": 4,
                "outlettype": ["", "int", "", ""],
                "fontsize": 10.0,
                "border": 0,
                "keymode": 1,
                "outputmode": 1,
                "readonly": 1,
                "varname": "status",
            }
        }
    )
    boxes.append(
        {
            "box": {
                "id": "obj-rows",
                "maxclass": "number",
                "patching_rect": [210, 140, 50, 22],
                "presentation": 1,
                "presentation_rect": [400, 28, 44, 16],
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", "bang"],
                "fontsize": 10.0,
                "parameter_enable": 0,
                "triscale": 0.9,
            }
        }
    )
    boxes.append(newobj("obj-unpack", "unpack 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0", 20, 160, 420, 24))
    boxes.append(newobj("obj-savedlg", "savedialog dataset.csv", 400, 200, 160, 1))
    boxes.append(newobj("obj-opendlg", "opendialog dataset.csv", 400, 230, 160, 1))
    boxes.append(message("msg-save", "save $1", 580, 200, 80))
    boxes.append(message("msg-load", "load $1", 580, 230, 80))
    boxes.append(newobj("sel-learn", "sel 1", 20, 260, 40, 2))
    boxes.append(newobj("sel-train", "sel 1", 70, 260, 40, 2))
    boxes.append(newobj("sel-bind", "sel 1", 120, 260, 40, 2))
    boxes.append(newobj("sel-save", "sel 1", 170, 260, 40, 2))
    boxes.append(newobj("sel-load", "sel 1", 220, 260, 40, 2))
    boxes.append(newobj("sel-clear", "sel 1", 270, 260, 40, 2))
    boxes.append(newobj("sel-q4", "sel 1", 320, 260, 40, 2))
    boxes.append(newobj("sel-q8", "sel 1", 370, 260, 40, 2))
    boxes.append(message("msg-learn", "learn", 20, 290, 50))
    boxes.append(message("msg-train", "train", 70, 290, 50))
    boxes.append(message("msg-bind", "bind", 120, 290, 50))
    boxes.append(message("msg-clear", "clear", 270, 290, 50))
    boxes.append(message("msg-q4", "division 4", 320, 290, 70))
    boxes.append(message("msg-q8", "division 8", 400, 290, 70))
    boxes.append(newobj("pre-col", "prepend col", 20, 330, 80, 1))
    boxes.append(newobj("pre-rhy", "prepend rhy", 110, 330, 80, 1))
    boxes.append(newobj("pre-dyn", "prepend dyn", 200, 330, 80, 1))
    boxes.append(newobj("pre-heart", "prepend heart", 290, 330, 90, 1))
    boxes.append(newobj("pre-wet", "prepend drywet", 390, 330, 90, 1))

    for i in range(8):
        boxes.append(newobj(f"pre-s{i}", f"prepend send {i}", 20 + i * 90, 620, 80, 1))
        boxes.append(newobj(f"pre-p{i}", f"prepend prob {i}", 20 + i * 90, 650, 80, 1))
        boxes.append(newobj(f"pre-d{i}", f"prepend dynam {i}", 20 + i * 90, 680, 90, 1))

    # Wiring
    lines.append(line("obj-this", 0, "obj-js", 0))
    lines.append(line("obj-js", 0, "obj-status", 0))
    lines.append(line("obj-js", 1, "obj-unpack", 0))
    lines.append(line("obj-js", 2, "obj-rows", 0))

    for src, sel, msg in [
        ("btn-learn", "sel-learn", "msg-learn"),
        ("btn-train", "sel-train", "msg-train"),
        ("btn-bind", "sel-bind", "msg-bind"),
        ("btn-clear", "sel-clear", "msg-clear"),
        ("btn-q4", "sel-q4", "msg-q4"),
        ("btn-q8", "sel-q8", "msg-q8"),
    ]:
        lines.append(line(src, 0, sel, 0))
        lines.append(line(sel, 0, msg, 0))
        lines.append(line(msg, 0, "obj-js", 0))

    lines.append(line("btn-save", 0, "sel-save", 0))
    lines.append(line("sel-save", 0, "obj-savedlg", 0))
    lines.append(line("obj-savedlg", 0, "msg-save", 0))
    lines.append(line("msg-save", 0, "obj-js", 0))

    lines.append(line("btn-load", 0, "sel-load", 0))
    lines.append(line("sel-load", 0, "obj-opendlg", 0))
    lines.append(line("obj-opendlg", 0, "msg-load", 0))
    lines.append(line("msg-load", 0, "obj-js", 0))

    lines.append(line("dial-col", 0, "pre-col", 0))
    lines.append(line("dial-rhy", 0, "pre-rhy", 0))
    lines.append(line("dial-dyn", 0, "pre-dyn", 0))
    lines.append(line("dial-heart", 0, "pre-heart", 0))
    lines.append(line("dial-wet", 0, "pre-wet", 0))
    for pre in ("pre-col", "pre-rhy", "pre-dyn", "pre-heart", "pre-wet"):
        lines.append(line(pre, 0, "obj-js", 0))

    for i in range(8):
        lines.append(line(f"dial-s{i}", 0, f"pre-s{i}", 0))
        lines.append(line(f"pre-s{i}", 0, "obj-js", 0))
        lines.append(line(f"nb-p{i}", 0, f"pre-p{i}", 0))
        lines.append(line(f"pre-p{i}", 0, "obj-js", 0))
        lines.append(line(f"nb-d{i}", 0, f"pre-d{i}", 0))
        lines.append(line(f"pre-d{i}", 0, "obj-js", 0))
        # predicted sends/faders drive the preview sliders (first 8 of unpack)
        # Preview only. Do not write back into send dials (that would
        # overwrite the training graphics).
        lines.append(line("obj-unpack", i, f"sl-f{i}", 0))

    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {
                "major": 9,
                "minor": 0,
                "revision": 10,
                "architecture": "x64",
                "modernui": 1,
            },
            "classnamespace": "box",
            "rect": [80.0, 80.0, W, H + 40],
            "openrect": [0.0, 0.0, W, H],
            "default_fontsize": 10.0,
            "default_fontname": "Ableton Sans Medium",
            "gridsize": [8.0, 8.0],
            "boxes": boxes,
            "lines": lines,
            "openinpresentation": 1,
            "autosave": 0,
            "isfront": 0,
            "description": "User-trained MLP assistant for real-time dub mixing.",
            "digest": "Maps col / rhy / dyn onto eight sends and stochastic faders.",
            "tags": "dub, mixer, machine learning, performance",
            "dependency_cache": [
                {
                    "name": "dub-assistant.js",
                    "bootpath": ".",
                    "type": "TEXT",
                    "implicit": 1,
                }
            ],
        }
    }


def write_amxd(maxpat_bytes: bytes, dest: Path) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return tag + len(data).to_bytes(4, "little") + data

    payload = b""
    payload += chunk(b"ampf", b"mmmm")
    payload += chunk(b"meta", (1).to_bytes(4, "little"))
    payload += chunk(b"ptch", maxpat_bytes + b"\x00")
    dest.write_bytes(payload)


def write_sample_dataset(path: Path) -> None:
    header = ["col", "rhy", "dyn"] + [f"y{i}" for i in range(24)]
    rows = []

    def vec(col, rhy, dyn):
        sends = [min(1.0, col * (0.45 + 0.07 * (i % 4))) for i in range(8)]
        prob = [min(1.0, rhy * (0.35 if i < 2 else 0.85)) for i in range(8)]
        dynam = [dyn] * 8
        return [col, rhy, dyn] + sends + prob + dynam

    grid = (0.1, 0.5, 0.9)
    for c in grid:
        for r in grid:
            for d in grid:
                rows.append(vec(c, r, d))
    # Extra dub-leaning rows: dry rhythm, wet colour, isolated drums/bass
    rows.append(vec(0.15, 0.85, 0.7))
    rows.append(vec(0.8, 0.25, 0.4))
    rows.append(vec(0.55, 0.6, 0.9))

    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(f"{v:.4f}" for v in row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    DEVICE.mkdir(parents=True, exist_ok=True)
    patch = build_patcher()
    maxpat_path = DEVICE / "Dub Assistant.maxpat"
    text = json.dumps(patch, indent="\t")
    maxpat_path.write_text(text, encoding="utf-8")
    raw = text.encode("utf-8")
    amxd_path = DEVICE / "Dub Assistant.amxd"
    write_amxd(raw, amxd_path)
    sample = DEVICE / "sample-dataset.csv"
    write_sample_dataset(sample)

    USER_LIB.mkdir(parents=True, exist_ok=True)
    for name in (
        "Dub Assistant.amxd",
        "Dub Assistant.maxpat",
        "dub-assistant.js",
        "sample-dataset.csv",
    ):
        shutil.copy2(DEVICE / name, USER_LIB / name)
    print("wrote", maxpat_path)
    print("wrote", amxd_path, "bytes", amxd_path.stat().st_size)
    print("copied to", USER_LIB)


if __name__ == "__main__":
    main()
