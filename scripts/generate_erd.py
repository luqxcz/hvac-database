import os
import sys
from pathlib import Path
from typing import List

from graphviz import Digraph

sys.path.append(str(Path(__file__).resolve().parents[1]))
from db import Base  # noqa: E402


def _escape(text: str) -> str:
    return (
        text.replace("<", "\u003c").replace(">", "\u003e").replace("|", "\u007c").replace("{", "(").replace("}", ")")
    )


def _column_flags(col) -> List[str]:
    flags: List[str] = []
    if getattr(col, "primary_key", False):
        flags.append("PK")
    if getattr(col, "nullable", True) is False:
        flags.append("NN")
    if col.foreign_keys:
        flags.append("FK")
    return flags


def build_graph() -> Digraph:
    g = Digraph("ERD", graph_attr={"rankdir": "LR"}, node_attr={"shape": "record", "fontname": "Helvetica"})

    # Nodes
    for table_name, table in Base.metadata.tables.items():
        field_lines: List[str] = []
        for col in table.columns:
            col_type = str(col.type)
            flags = _column_flags(col)
            flag_str = f" ({', '.join(flags)})" if flags else ""
            port = f"{col.name}"
            field_lines.append(f"<{port}> {col.name}: {_escape(col_type)}{flag_str}")

        fields_block = "|".join(field_lines) if field_lines else ""
        label = f"{{{table_name}|{{{fields_block}}}}}"
        g.node(table_name, label=label)

    # Edges (FKs)
    for table_name, table in Base.metadata.tables.items():
        for col in table.columns:
            for fk in col.foreign_keys:
                ref_table = fk.column.table.name
                ref_col = fk.column.name
                g.edge(f"{table_name}:{col.name}", f"{ref_table}:{ref_col}", arrowhead="normal")

    return g


def main() -> None:
    out_dir = Path(os.getenv("OUT_DIR", "docs"))
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "db_erd.png"
    svg_path = out_dir / "db_erd.svg"
    dot_path = out_dir / "db_erd.dot"

    g = build_graph()
    dot_path.write_text(g.source, encoding="utf-8")
    g.format = "png"
    g.render(filename=str(png_path.with_suffix("").as_posix()), cleanup=True)
    g.format = "svg"
    g.render(filename=str(svg_path.with_suffix("").as_posix()), cleanup=True)
    print(f"Wrote {png_path}, {svg_path}, and {dot_path}")


if __name__ == "__main__":
    main()


