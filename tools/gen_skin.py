"""Assemble SkinDefinition.xml from generated art plus optional layout modules.

A LOTRO skin is one XML file with two halves:

  <Mapping ArtAssetID="..." FileName="..."/>   replace a piece of art
  <PanelFile ID="..."><Element ID="..." .../>  move / resize / hide a panel part

The art half is safe everywhere. The layout half is resolution-dependent, so
layout fragments are templates: `{{ expr }}` is evaluated against the profile's
variables, and `<!-- @if flag -->` blocks are kept only when the flag is set.
"""

from __future__ import annotations

import ast
import operator
import re
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

TEMPLATE_TOKEN = re.compile(r"\{\{(.+?)\}\}")
IF_BLOCK = re.compile(
    r"[ \t]*<!--\s*@if\s+(!?)([A-Za-z_][A-Za-z0-9_]*)\s*-->\n?(.*?)[ \t]*<!--\s*@endif\s*-->\n?",
    re.DOTALL,
)

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class TemplateError(ValueError):
    pass


def evaluate(expression: str, variables: dict) -> float:
    """Evaluate a small arithmetic expression over `variables`.

    Deliberately not `eval`: only numbers, names, arithmetic and min/max/round
    are reachable, so a layout fragment can never run arbitrary code.
    """
    allowed_calls = {"min": min, "max": max, "round": round, "int": int, "abs": abs}

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise TemplateError(f"only numeric constants allowed, got {node.value!r}")
        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise TemplateError(
                    f"unknown variable '{node.id}' in expression '{expression.strip()}'"
                )
            return variables[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
            return _BINARY_OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](walk(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in allowed_calls:
                raise TemplateError(f"function '{node.func.id}' is not allowed")
            return allowed_calls[node.func.id](*[walk(a) for a in node.args])
        raise TemplateError(f"unsupported syntax in expression '{expression.strip()}'")

    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise TemplateError(f"cannot parse '{expression.strip()}': {exc}") from exc
    return walk(tree)


def render_template(text: str, variables: dict, flags: dict) -> str:
    """Resolve @if blocks first, then {{ }} expressions."""

    def resolve_block(match: re.Match) -> str:
        negate, name, body = match.group(1), match.group(2), match.group(3)
        enabled = bool(flags.get(name, False))
        if negate:
            enabled = not enabled
        return body if enabled else ""

    # Loop so nested @if blocks collapse from the inside out.
    previous = None
    while previous != text:
        previous = text
        text = IF_BLOCK.sub(resolve_block, text)

    def resolve_expr(match: re.Match) -> str:
        value = evaluate(match.group(1), variables)
        # LOTRO wants integers for coordinates; keep the XML free of "720.0".
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        elif isinstance(value, float):
            value = int(round(value))
        return str(value)

    return TEMPLATE_TOKEN.sub(resolve_expr, text)


def build_variables(profile: dict) -> dict:
    width, height = profile.get("resolution", [1920, 1080])
    options = profile.get("options", {})
    variables = {
        "screenWidth": int(width),
        "screenHeight": int(height),
    }
    for key, value in options.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            variables[key] = value
    return variables


def build_flags(profile: dict) -> dict:
    return {
        key: value
        for key, value in profile.get("options", {}).items()
        if isinstance(value, bool)
    }


COMMENT_BLOCK = re.compile(r"<!--(.*?)-->", re.DOTALL)


def check_comments(text: str, source: Path) -> None:
    """XML forbids a double hyphen inside a comment, and the game's only
    reaction to malformed XML is to drop the skin from the list without a word.
    Catching it here costs one regex and saves a confusing evening."""
    for match in COMMENT_BLOCK.finditer(text):
        body = match.group(1)
        if "--" in body:
            line = text.count("\n", 0, match.start() + body.find("--")) + 1
            raise TemplateError(
                f"{source}:{line}: XML comments cannot contain '--'. "
                "Rephrase with a comma, a colon or a single hyphen."
            )


def render_layout_modules(
    layout_dir: str | Path, modules: list[str], profile: dict
) -> tuple[str, list[str]]:
    """Render each enabled fragment. Returns (xml, names of modules used)."""
    layout_dir = Path(layout_dir)
    variables = build_variables(profile)
    flags = build_flags(profile)

    chunks: list[str] = []
    used: list[str] = []
    for name in modules:
        path = layout_dir / f"{name}.xml"
        if not path.exists():
            raise FileNotFoundError(
                f"layout module '{name}' not found at {path}. "
                f"Available: {', '.join(sorted(p.stem for p in layout_dir.glob('*.xml'))) or 'none'}"
            )
        raw = path.read_text(encoding="utf-8")
        check_comments(raw, path)
        rendered = render_template(raw, variables, flags).strip()
        if rendered:
            chunks.append(f"<!-- layout module: {name} -->\n{rendered}")
            used.append(name)
    return "\n\n".join(chunks), used


def write_skin_definition(
    out_path: str | Path,
    skin_name: str,
    art_records: list[dict],
    layout_xml: str,
    header_note: str = "",
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Match the conventions of skins that are known to load, rather than
    # relying on the client's XML parser being as forgiving as Python's:
    # the header comment goes inside <opt>, Mapping uses an explicit closing
    # tag rather than self-closing, and paths carry a leading ".\".
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<opt>",
        "<!--",
        f"  {escape(header_note)}" if header_note else "  MithrilUI",
        "",
        "  GENERATED FILE - do not edit by hand.",
        "  Rebuild with: python tools/build.py",
        "-->",
        f"<SkinName Name={quoteattr(skin_name)}></SkinName>",
        "",
    ]

    if art_records:
        by_module: dict[str, list[dict]] = {}
        for record in art_records:
            by_module.setdefault(record["module"], []).append(record)

        lines.append(f"<!-- ART MAPPINGS ({len(art_records)} assets) -->")
        for module in sorted(by_module):
            lines.append(f"<!-- {module} -->")
            for record in sorted(by_module[module], key=lambda r: r["id"]):
                path = record["file"]
                if not path.startswith(".\\"):
                    path = ".\\" + path.lstrip("\\")
                lines.append(
                    f'<Mapping ArtAssetID={quoteattr(record["id"])} '
                    f'FileName={quoteattr(path)}></Mapping>'
                )
            lines.append("")

    if layout_xml:
        lines.append("<!-- PANEL LAYOUT -->")
        lines.append(layout_xml)
        lines.append("")

    lines.append("</opt>")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
