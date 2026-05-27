#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
LABEL_RE = re.compile(r"^([A-Za-z_.$][\w.$]*)(::?)\s*(.*)$")
ASSIGN_RE = re.compile(r"^([A-Za-z_.$][\w.$]*)\s*=\s*(.+)$")


def load_script_command_constants() -> Dict[str, int]:
    constants = {}
    value = 0
    table = ROOT / "data/script_cmd_table.inc"
    for line in table.read_text().splitlines():
        line = line.split("@", 1)[0].strip()
        if line.startswith("script_cmd_table_entry "):
            constants[line.split()[1]] = value
            value += 1
    return constants


def preprocess(source: Path) -> str:
    first = subprocess.run(
        [str(ROOT / "tools/preproc/preproc"), str(source), "charmap.txt"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    cpp = subprocess.run(
        ["clang", "-E", "-x", "assembler-with-cpp", "-I", "include", "-"],
        cwd=ROOT,
        input=first.stdout,
        check=True,
        text=True,
        capture_output=True,
    )
    second = subprocess.run(
        [str(ROOT / "tools/preproc/preproc"), "-ie", str(source), "charmap.txt"],
        cwd=ROOT,
        input=cpp.stdout,
        check=True,
        text=True,
        capture_output=True,
    )
    return second.stdout


def parse_int(expr: str, constants: Dict[str, int]) -> int:
    return int(eval(expr.strip(), {"__builtins__": {}}, constants))


def split_args(text: str) -> List[str]:
    return [arg.strip() for arg in text.split(",")]


def expand_macro(stripped: str, constants: Dict[str, int], counters: Dict[str, int]) -> Optional[List[str]]:
    if stripped.startswith("map_script "):
        script_type, script = split_args(stripped[len("map_script "):])
        return [f".byte {script_type}", f".4byte {script}"]

    if stripped == "end":
        return [f".byte {parse_int('SCR_OP_END', constants)}"]

    if stripped == "lockall":
        return [f".byte {parse_int('SCR_OP_LOCKALL', constants)}"]

    if stripped == "releaseall":
        return [f".byte {parse_int('SCR_OP_RELEASEALL', constants)}"]

    if stripped == "checkplayergender":
        return [f".byte {parse_int('SCR_OP_CHECKPLAYERGENDER', constants)}"]

    if stripped.startswith("setmetatile "):
        x, y, metatile, impassable = split_args(stripped[len("setmetatile "):])
        return [f".byte {parse_int('SCR_OP_SETMETATILE', constants)}", f".2byte {x}", f".2byte {y}", f".2byte {metatile}", f".2byte {impassable}"]

    if stripped.startswith("setstepcallback "):
        step = stripped[len("setstepcallback "):].strip()
        return [f".byte {parse_int('SCR_OP_SETSTEPCALLBACK', constants)}", f".byte {step}"]

    if stripped.startswith("setflag "):
        flag = stripped[len("setflag "):].strip()
        return [f".byte {parse_int('SCR_OP_SETFLAG', constants)}", f".2byte {flag}"]

    if stripped.startswith("setrespawn "):
        heal_location = stripped[len("setrespawn "):].strip()
        return [f".byte {parse_int('SCR_OP_SETRESPAWN', constants)}", f".2byte {heal_location}"]

    if stripped.startswith("setvar "):
        var, value = split_args(stripped[len("setvar "):])[:2]
        return [f".byte {parse_int('SCR_OP_SETVAR', constants)}", f".2byte {var}", f".2byte {value}"]

    if stripped.startswith("goto_if_eq "):
        var, value, destination = split_args(stripped[len("goto_if_eq "):])
        return [
            f".byte {parse_int('SCR_OP_COMPARE_VAR_TO_VALUE', constants)}",
            f".2byte {var}",
            f".2byte {value}",
            f".byte {parse_int('SCR_OP_GOTO_IF', constants)}",
            ".byte 1",
            f".4byte {destination}",
        ]

    if stripped.startswith("setdynamicwarp "):
        args = split_args(stripped[len("setdynamicwarp "):])
        map_value = parse_int(args[0], constants)
        lines = [
            f".byte {parse_int('SCR_OP_SETDYNAMICWARP', constants)}",
            f".byte {map_value >> 8}",
            f".byte {map_value & 0xFF}",
        ]
        if len(args) == 2:
            lines.extend([f".byte {args[1]}", ".2byte -1", ".2byte -1"])
        elif len(args) == 3:
            lines.extend([f".byte {parse_int('WARP_ID_NONE', constants)}", f".2byte {args[1]}", f".2byte {args[2]}"])
        elif len(args) == 4:
            lines.extend([f".byte {args[1]}", f".2byte {args[2]}", f".2byte {args[3]}"])
        else:
            lines.extend([f".byte {parse_int('WARP_ID_NONE', constants)}", ".2byte -1", ".2byte -1"])
        return lines

    if stripped.startswith("msgbox "):
        text, msgbox_type = split_args(stripped[len("msgbox "):])
        return [
            f".byte {parse_int('SCR_OP_LOAD_WORD', constants)}",
            ".byte 0",
            f".4byte {text}",
            f".byte {parse_int('SCR_OP_CALL_STD', constants)}",
            f".byte {msgbox_type}",
        ]

    if stripped == "reset_map_events":
        counters.update(npcs=0, warps=0, traps=0, signs=0)
        return []

    if stripped.startswith("object_event "):
        args = split_args(stripped[len("object_event "):])
        counters["npcs"] += 1
        return [
            f".byte {args[0]}",
            f".byte {args[1]}",
            f".byte {parse_int('OBJ_KIND_NORMAL', constants)}",
            ".space 1",
            f".2byte {args[2]}, {args[3]}",
            f".byte {args[4]}",
            f".byte {args[5]}",
            f".byte ((({args[7]}) << 4) | ({args[6]}))",
            ".space 1",
            f".2byte {args[8]}",
            f".2byte {args[9]}",
            f".4byte {args[10]}",
            f".2byte {args[11]}",
            ".space 2",
        ]

    if stripped.startswith("warp_def "):
        x, y, elevation, warp_id, map_id = split_args(stripped[len("warp_def "):])
        map_value = parse_int(map_id, constants)
        counters["warps"] += 1
        return [
            f".2byte {x}, {y}",
            f".byte {elevation}",
            f".byte {warp_id}",
            f".byte {map_value & 0xFF}",
            f".byte {map_value >> 8}",
        ]

    if stripped.startswith("coord_weather_event "):
        x, y, elevation, weather = split_args(stripped[len("coord_weather_event "):])
        stripped = f"coord_event {x}, {y}, {elevation}, {weather}, 0, 0"

    if stripped.startswith("coord_event "):
        x, y, elevation, var, var_value, script = split_args(stripped[len("coord_event "):])
        counters["traps"] += 1
        return [
            f".2byte {x}, {y}",
            f".byte {elevation}",
            ".space 1",
            f".2byte {var}",
            f".2byte {var_value}",
            ".space 2",
            f".4byte {script}",
        ]

    if stripped.startswith("bg_sign_event "):
        x, y, elevation, facing_dir, script = split_args(stripped[len("bg_sign_event "):])
        stripped = f"bg_event {x}, {y}, {elevation}, {facing_dir}, {script}"

    if stripped.startswith("bg_hidden_item_event "):
        x, y, elevation, item, flag = split_args(stripped[len("bg_hidden_item_event "):])
        hidden_item = parse_int("BG_EVENT_HIDDEN_ITEM", constants)
        flag_start = parse_int("FLAG_HIDDEN_ITEMS_START", constants)
        stripped = f"bg_event {x}, {y}, {elevation}, {hidden_item}, {item}, (({flag}) - {flag_start})"

    if stripped.startswith("bg_secret_base_event "):
        x, y, elevation, secret_base_id = split_args(stripped[len("bg_secret_base_event "):])
        secret_base = parse_int("BG_EVENT_SECRET_BASE", constants)
        stripped = f"bg_event {x}, {y}, {elevation}, {secret_base}, {secret_base_id}"

    if stripped.startswith("bg_event "):
        args = split_args(stripped[len("bg_event "):])
        x, y, elevation, kind, arg6 = args[:5]
        kind_value = parse_int(kind, constants)
        counters["signs"] += 1
        lines = [
            f".2byte {x}, {y}",
            f".byte {elevation}",
            f".byte {kind}",
            ".space 2",
        ]
        if kind_value == parse_int("BG_EVENT_HIDDEN_ITEM", constants):
            lines.extend([f".2byte {arg6}", f".2byte {args[5]}"])
        else:
            lines.append(f".4byte {arg6}")
        return lines

    if stripped.startswith("map_events "):
        npcs, warps, traps, signs = split_args(stripped[len("map_events "):])
        lines = [
            f".byte {counters['npcs']}, {counters['warps']}, {counters['traps']}, {counters['signs']}",
            f".4byte {npcs}, {warps}, {traps}, {signs}",
        ]
        counters.update(npcs=0, warps=0, traps=0, signs=0)
        return lines

    if stripped.startswith("map_header_flags "):
        values = {}
        for arg in split_args(stripped[len("map_header_flags "):]):
            key, value = arg.split("=", 1)
            values[key.strip()] = parse_int(value, constants)
        byte = (
            ((values["show_map_name"] & 1) << 3)
            | ((values["allow_running"] & 1) << 2)
            | ((values["allow_escaping"] & 1) << 1)
            | (values["allow_cycling"] & 1)
        )
        return [f".byte {byte}"]

    if stripped.startswith("connection "):
        direction, offset, map_id = split_args(stripped[len("connection "):])
        connection_id = constants[f"connection_{direction}"]
        map_value = parse_int(map_id, constants)
        return [
            f".byte {connection_id}",
            ".space 3",
            f".4byte {parse_int(offset, constants)}",
            f".byte {map_value >> 8}",
            f".byte {map_value & 0xFF}",
            ".space 2",
        ]

    if stripped.startswith("map "):
        map_value = parse_int(stripped[len("map "):], constants)
        return [f".byte {map_value >> 8}", f".byte {map_value & 0xFF}"]

    return None


def strip_at_comment(line: str) -> str:
    in_quote = False
    escaped = False
    for i, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            in_quote = not in_quote
        elif char in "@;" and not in_quote:
            return line[:i].rstrip()
    return line.rstrip()


def convert(text: str) -> str:
    out = []
    constants = load_script_command_constants()
    constants.update({
        "OBJ_KIND_NORMAL": 0,
        "OBJ_KIND_CLONE": 1,
        "BG_EVENT_HIDDEN_ITEM": 7,
        "BG_EVENT_SECRET_BASE": 8,
        "FLAG_HIDDEN_ITEMS_START": 0x1F4,
        "NULL": 0,
        "WARP_ID_NONE": 0x7F,
        "MSGBOX_SIGN": 3,
        "STEP_CB_TRUCK": 5,
    })
    counters = {"npcs": 0, "warps": 0, "traps": 0, "signs": 0}
    open_label = None

    def close_label():
        nonlocal open_label
        if open_label:
            out.append(f".size {open_label}, .-{open_label}")
            open_label = None

    skip_macro = 0
    for raw in text.splitlines():
        is_global_label = "; .global" in raw
        line = strip_at_comment(raw)
        if not line or line.startswith("#"):
            continue

        stripped = line.strip()
        if skip_macro:
            if stripped.startswith(".macro "):
                skip_macro += 1
            elif stripped == ".endm":
                skip_macro -= 1
            continue
        if stripped.startswith(".macro "):
            skip_macro = 1
            continue
        if (
            stripped.startswith("enum_start ")
            or stripped.startswith("enum ")
            or stripped.startswith("create_movement_action ")
            or stripped in {"reset_map_events", "inc _num_npcs", "inc _num_warps", "inc _num_traps", "inc _num_signs"}
        ):
            continue
        assignment = ASSIGN_RE.match(stripped)
        if stripped.startswith(".equiv ") or stripped.startswith(".set "):
            name, expr = re.split(r"\s+", stripped, maxsplit=1)[1].split(",", 1)
            try:
                constants[name.strip()] = eval(expr, {"__builtins__": {}}, constants)
            except Exception:
                pass
            continue
        if assignment:
            name, expr = assignment.groups()
            try:
                constants[name] = eval(expr, {"__builtins__": {}}, constants)
            except Exception:
                pass
            continue

        if constants:
            stripped = re.sub(
                r"\b[A-Z][A-Z0-9_]*\b",
                lambda match: str(constants.get(match.group(0), match.group(0))),
                stripped,
            )

        macro = expand_macro(stripped, constants, counters)
        if macro:
            out.extend(macro)
            continue

        if stripped.startswith(".section"):
            close_label()
            section = stripped.split()[1].split(",", 1)[0]
            out.append(f".section {section},\"\",@")
            continue

        match = LABEL_RE.match(stripped)
        if match:
            name, colons, rest = match.groups()
            close_label()
            if colons == "::" or is_global_label:
                out.append(f".globl {name}")
            out.append(f"{name}:")
            open_label = name
            if rest:
                out.append(rest)
            continue

        out.append(stripped)

    close_label()
    return "\n".join(out) + "\n"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: wasm_asm_data.py <source.s> <output.s>")
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(convert(preprocess(source)))


if __name__ == "__main__":
    main()
