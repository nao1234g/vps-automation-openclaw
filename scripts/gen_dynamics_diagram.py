"""
Nowpattern Dynamics Diagram Generator v1.0
力学ダイアグラムを自動生成する（Stratecheryの手描きダイアグラムの自動化版）。

4タイプ:
  1. flow     - フロー図（箱+矢印）: 力学の因果関係を可視化
  2. before_after - Before/After比較: 制度変更・市場構造の変化
  3. layers   - レイヤー図: 市場の層構造を水平棒で表示
  4. matrix   - 2×2マトリクス: 戦略ポジショニング

使い方:
  from gen_dynamics_diagram import generate_dynamics_diagram

  svg = generate_dynamics_diagram(
      diagram_type="flow",
      title="プラットフォーム支配 × 規制の捕獲",
      nodes=[
          {"id": "apple", "label": "Apple\\n(App Store)", "type": "power"},
          {"id": "devs", "label": "開発者\\n(200万人)", "type": "affected"},
          {"id": "eu", "label": "EU\\n(DMA)", "type": "regulator"},
      ],
      edges=[
          {"from": "apple", "to": "devs", "label": "30%手数料", "type": "dominance"},
          {"from": "apple", "to": "eu", "label": "ロビイング", "type": "capture"},
          {"from": "eu", "to": "apple", "label": "制裁金€1.8B", "type": "regulation"},
      ],
      output_path="diagram.svg"
  )
"""

from __future__ import annotations
from pathlib import Path


# ---------------------------------------------------------------------------
# Color palette (Nowpattern brand)
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#ffffff",
    "navy": "#121e30",
    "gold": "#c9a84c",
    "white": "#ffffff",
    "red": "#c0392b",
    "green": "#27ae60",
    "light_gray": "#e0dcd4",
    "mid_gray": "#888888",
    "text": "#121e30",
}

NODE_COLORS = {
    "power":     {"fill": "#121e30", "text": "#c9a84c", "stroke": "#c9a84c"},  # 濃紺+金 — 支配者
    "affected":  {"fill": "#dbeafe", "text": "#1e3a5f", "stroke": "#3b82f6"},  # 水色 — 影響を受ける側
    "regulator": {"fill": "#14532d", "text": "#ffffff", "stroke": "#22c55e"},  # 深緑 — 規制者
    "neutral":   {"fill": "#f9fafb", "text": "#374151", "stroke": "#9ca3af"},  # 薄グレー — 中立
}

EDGE_COLORS = {
    "dominance": "#c9a84c",   # gold — 支配・制御
    "capture": "#FF1A75",     # pink — 取り込み・操作
    "regulation": "#27ae60",  # green — 規制・法的圧力
    "feedback": "#c9a84c",    # gold — フィードバックループ
    "resistance": "#b0a090",  # muted — 抵抗・反発
    "neutral": "#888888",     # gray — 中立
    "flow": "#121e30",        # navy — 基本フロー
}


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _svg_header(width: int = 960, height: int = 680) -> str:
    # width="100%" + viewBox でGhost記事幅いっぱいにレスポンシブ表示
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:100%; display:block; '
        f'font-family: \'Noto Sans CJK JP\', \'Noto Sans\', sans-serif;">\n'
        f'  <rect width="{width}" height="{height}" fill="{COLORS["bg"]}" rx="4"/>\n'
    )


def _svg_footer() -> str:
    return '</svg>\n'


def _svg_rounded_rect(x: float, y: float, w: float, h: float,
                       fill: str, stroke: str, rx: int = 8) -> str:
    return (
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
    )


def _svg_text(x: float, y: float, text: str, fill: str = "#121e30",
              size: int = 14, anchor: str = "middle", bold: bool = False) -> str:
    weight = 'font-weight="bold"' if bold else ''
    lines = text.split("\\n")
    if len(lines) == 1:
        return (
            f'  <text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'fill="{fill}" font-size="{size}" {weight}>{text}</text>\n'
        )
    result = ""
    for i, line in enumerate(lines):
        dy = size * 1.2 * i - (size * 1.2 * (len(lines) - 1)) / 2
        result += (
            f'  <text x="{x}" y="{y + dy}" text-anchor="{anchor}" '
            f'fill="{fill}" font-size="{size}" {weight}>{line}</text>\n'
        )
    return result


def _svg_arrow(x1: float, y1: float, x2: float, y2: float,
               color: str = "#121e30", label: str = "") -> str:
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    head_len = 10
    # Shorten the line so arrow doesn't overlap with box
    shorten = 15
    dx = math.cos(angle) * shorten
    dy = math.sin(angle) * shorten
    ax2 = x2 - dx
    ay2 = y2 - dy

    # Arrow head points
    lx = ax2 - head_len * math.cos(angle - 0.4)
    ly = ay2 - head_len * math.sin(angle - 0.4)
    rx = ax2 - head_len * math.cos(angle + 0.4)
    ry = ay2 - head_len * math.sin(angle + 0.4)

    result = (
        f'  <line x1="{x1 + dx}" y1="{y1 + dy}" x2="{ax2}" y2="{ay2}" '
        f'stroke="{color}" stroke-width="2.5"/>\n'
        f'  <polygon points="{ax2},{ay2} {lx},{ly} {rx},{ry}" fill="{color}"/>\n'
    )

    if label:
        # ラベルをソースノードから25%の位置に配置（交差矢印でのラベル重なりを防ぐ）
        mx = x1 + (x2 - x1) * 0.25
        my = y1 + (y2 - y1) * 0.25 - 16
        # 白背景ボックスでラベルを見やすく（他の矢印と重なっても読める）
        lw = len(label) * 14 + 16  # 日本語1文字≒14px
        lh = 24
        result += (
            f'  <rect x="{mx - lw/2:.1f}" y="{my - lh/2 + 4:.1f}" '
            f'width="{lw}" height="{lh}" fill="white" opacity="0.94" rx="4" '
            f'stroke="{color}" stroke-width="1"/>\n'
        )
        result += _svg_text(mx, my + 13, label, fill=color, size=14)

    return result


# ---------------------------------------------------------------------------
# Diagram generators
# ---------------------------------------------------------------------------

def _generate_flow(title: str, nodes: list[dict], edges: list[dict],
                   width: int = 960, height: int = 760) -> str:
    """フロー図（箱+矢印）を生成"""
    LEGEND_H = 90  # 下部凡例エリアの高さ
    chart_h = height - LEGEND_H  # ノード配置に使える縦幅

    svg = _svg_header(width, height)

    # Title
    svg += _svg_text(width / 2, 44, title, fill=COLORS["navy"], size=26, bold=True)

    # Position nodes in a layout
    n = len(nodes)
    node_w, node_h = 200, 90
    positions = {}

    if n <= 3:
        # Horizontal layout
        spacing = width / (n + 1)
        for i, node in enumerate(nodes):
            x = spacing * (i + 1) - node_w / 2
            y = chart_h / 2 - node_h / 2 + 10
            positions[node["id"]] = (x + node_w / 2, y + node_h / 2)
            colors = NODE_COLORS.get(node.get("type", "neutral"), NODE_COLORS["neutral"])
            svg += _svg_rounded_rect(x, y, node_w, node_h, colors["fill"], colors["stroke"])
            svg += _svg_text(x + node_w / 2, y + node_h / 2 + 7, node["label"],
                           fill=colors["text"], size=18, bold=True)
    elif n <= 6:
        # Two-row layout
        top_count = (n + 1) // 2
        bot_count = n - top_count
        top_y = chart_h * 0.22
        bot_y = chart_h * 0.58
        for i in range(top_count):
            node = nodes[i]
            spacing = width / (top_count + 1)
            x = spacing * (i + 1) - node_w / 2
            positions[node["id"]] = (x + node_w / 2, top_y + node_h / 2)
            colors = NODE_COLORS.get(node.get("type", "neutral"), NODE_COLORS["neutral"])
            svg += _svg_rounded_rect(x, top_y, node_w, node_h, colors["fill"], colors["stroke"])
            svg += _svg_text(x + node_w / 2, top_y + node_h / 2 + 7, node["label"],
                           fill=colors["text"], size=17, bold=True)
        for i in range(bot_count):
            node = nodes[top_count + i]
            spacing = width / (bot_count + 1)
            x = spacing * (i + 1) - node_w / 2
            positions[node["id"]] = (x + node_w / 2, bot_y + node_h / 2)
            colors = NODE_COLORS.get(node.get("type", "neutral"), NODE_COLORS["neutral"])
            svg += _svg_rounded_rect(x, bot_y, node_w, node_h, colors["fill"], colors["stroke"])
            svg += _svg_text(x + node_w / 2, bot_y + node_h / 2 + 7, node["label"],
                           fill=colors["text"], size=17, bold=True)
    else:
        # Grid layout
        cols = 3
        rows = (n + cols - 1) // cols
        cell_w = width / (cols + 1)
        cell_h = (chart_h - 70) / (rows + 1)
        for i, node in enumerate(nodes):
            r, c = divmod(i, cols)
            x = cell_w * (c + 1) - node_w / 2
            y = 70 + cell_h * (r + 1) - node_h / 2
            positions[node["id"]] = (x + node_w / 2, y + node_h / 2)
            colors = NODE_COLORS.get(node.get("type", "neutral"), NODE_COLORS["neutral"])
            svg += _svg_rounded_rect(x, y, node_w, node_h, colors["fill"], colors["stroke"])
            svg += _svg_text(x + node_w / 2, y + node_h / 2 + 7, node["label"],
                           fill=colors["text"], size=15, bold=True)

    # Draw edges
    for edge in edges:
        src = positions.get(edge["from"])
        dst = positions.get(edge["to"])
        if src and dst:
            color = EDGE_COLORS.get(edge.get("type", "neutral"), EDGE_COLORS["neutral"])
            svg += _svg_arrow(src[0], src[1], dst[0], dst[1],
                            color=color, label=edge.get("label", ""))

    # ─── Legend box (bottom) ───────────────────────────────────────────────
    legend_top = height - LEGEND_H
    svg += (
        f'  <rect x="0" y="{legend_top}" width="{width}" height="{LEGEND_H}" '
        f'fill="#f4f2ee" rx="0"/>\n'
        f'  <line x1="0" y1="{legend_top}" x2="{width}" y2="{legend_top}" '
        f'stroke="{COLORS["light_gray"]}" stroke-width="1"/>\n'
    )
    svg += _svg_text(18, legend_top + 24, "凡例", fill=COLORS["navy"], size=14,
                     anchor="start", bold=True)

    # Row 1: ノードタイプ（色付き四角＋シンプルな名称のみ）
    node_legend = [
        ("支配者", NODE_COLORS["power"]["fill"]),
        ("影響を受ける側", NODE_COLORS["affected"]["fill"]),
        ("規制者・第三者", NODE_COLORS["regulator"]["fill"]),
    ]
    row1_y = legend_top + 26
    step = int(width * 0.28)
    start_x = 70
    for i, (label, bg) in enumerate(node_legend):
        lx = start_x + i * step
        svg += (
            f'  <rect x="{lx}" y="{row1_y - 10}" width="20" height="20" '
            f'rx="3" fill="{bg}" stroke="{COLORS["light_gray"]}" stroke-width="1.5"/>\n'
        )
        svg += _svg_text(lx + 28, row1_y + 4, label, fill=COLORS["navy"], size=13, anchor="start")

    # Row 2: エッジタイプ（矢印サンプル＋意味）
    edge_legend_items = [
        ("支配・制御", EDGE_COLORS["dominance"]),
        ("取り込み・操作", EDGE_COLORS["capture"]),
        ("規制・法的圧力", EDGE_COLORS["regulation"]),
        ("抵抗・反発", EDGE_COLORS["resistance"]),
    ]
    row2_y = legend_top + 64
    step2 = int(width * 0.22)
    start_x2 = 70
    for i, (label, color) in enumerate(edge_legend_items):
        lx = start_x2 + i * step2
        svg += (
            f'  <line x1="{lx}" y1="{row2_y - 4}" x2="{lx + 24}" y2="{row2_y - 4}" '
            f'stroke="{color}" stroke-width="3"/>\n'
            f'  <polygon points="{lx + 24},{row2_y - 4} {lx + 16},{row2_y - 9} {lx + 16},{row2_y + 1}" '
            f'fill="{color}"/>\n'
        )
        svg += _svg_text(lx + 30, row2_y + 1, label, fill=COLORS["navy"], size=13, anchor="start")

    svg += _svg_footer()
    return svg


def _generate_before_after(title: str, nodes: list[dict], edges: list[dict],
                            width: int = 960, height: int = 680) -> str:
    """Before/After比較図を生成"""
    svg = _svg_header(width, height)

    svg += _svg_text(width / 2, 30, title, fill=COLORS["navy"], size=18, bold=True)

    mid = width / 2

    # Before side
    svg += _svg_text(mid / 2, 65, "BEFORE", fill=COLORS["red"], size=16, bold=True)
    svg += f'  <line x1="{mid}" y1="50" x2="{mid}" y2="{height - 40}" stroke="{COLORS["light_gray"]}" stroke-width="2" stroke-dasharray="6,4"/>\n'

    # After side
    svg += _svg_text(mid + mid / 2, 65, "AFTER", fill=COLORS["green"], size=16, bold=True)

    # Split nodes into before/after
    before_nodes = [n for n in nodes if n.get("side", "before") == "before"]
    after_nodes = [n for n in nodes if n.get("side") == "after"]

    node_w, node_h = 130, 50

    # Draw before nodes
    positions = {}
    for i, node in enumerate(before_nodes):
        x = (mid / 2) - node_w / 2
        y = 90 + i * 80
        positions[node["id"]] = (x + node_w / 2, y + node_h / 2)
        colors = NODE_COLORS.get(node.get("type", "neutral"), NODE_COLORS["neutral"])
        svg += _svg_rounded_rect(x, y, node_w, node_h, colors["fill"], colors["stroke"])
        svg += _svg_text(x + node_w / 2, y + node_h / 2 + 5, node["label"],
                       fill=colors["text"], size=12, bold=True)

    # Draw after nodes
    for i, node in enumerate(after_nodes):
        x = mid + (mid / 2) - node_w / 2
        y = 90 + i * 80
        positions[node["id"]] = (x + node_w / 2, y + node_h / 2)
        colors = NODE_COLORS.get(node.get("type", "neutral"), NODE_COLORS["neutral"])
        svg += _svg_rounded_rect(x, y, node_w, node_h, colors["fill"], colors["stroke"])
        svg += _svg_text(x + node_w / 2, y + node_h / 2 + 5, node["label"],
                       fill=colors["text"], size=12, bold=True)

    # Draw edges
    for edge in edges:
        src = positions.get(edge["from"])
        dst = positions.get(edge["to"])
        if src and dst:
            color = EDGE_COLORS.get(edge.get("type", "neutral"), EDGE_COLORS["neutral"])
            svg += _svg_arrow(src[0], src[1], dst[0], dst[1],
                            color=color, label=edge.get("label", ""))

    svg += _svg_footer()
    return svg


def _generate_layers(title: str, nodes: list[dict], edges: list[dict],
                     width: int = 960, height: int = 680) -> str:
    """レイヤー図を生成"""
    svg = _svg_header(width, height)
    svg += _svg_text(width / 2, 30, title, fill=COLORS["navy"], size=18, bold=True)

    layer_h = 50
    margin = 40
    usable_w = width - margin * 2
    n = len(nodes)

    for i, node in enumerate(nodes):
        y = 60 + i * (layer_h + 15)
        colors = NODE_COLORS.get(node.get("type", "neutral"), NODE_COLORS["neutral"])
        svg += _svg_rounded_rect(margin, y, usable_w, layer_h, colors["fill"], colors["stroke"], rx=4)
        svg += _svg_text(width / 2, y + layer_h / 2 + 5, node["label"],
                       fill=colors["text"], size=14, bold=True)

    svg += _svg_footer()
    return svg


def _generate_matrix(title: str, nodes: list[dict], edges: list[dict],
                     width: int = 960, height: int = 680) -> str:
    """2×2マトリクスを生成"""
    svg = _svg_header(width, height)
    svg += _svg_text(width / 2, 30, title, fill=COLORS["navy"], size=18, bold=True)

    cx, cy = width / 2, height / 2 + 10
    qw, qh = 300, 170

    # Axes
    svg += f'  <line x1="{cx - qw}" y1="{cy}" x2="{cx + qw}" y2="{cy}" stroke="{COLORS["navy"]}" stroke-width="2"/>\n'
    svg += f'  <line x1="{cx}" y1="{cy - qh}" x2="{cx}" y2="{cy + qh}" stroke="{COLORS["navy"]}" stroke-width="2"/>\n'

    # Axis labels from edges (using first 2 edges as axis labels)
    if len(edges) >= 2:
        svg += _svg_text(cx + qw - 20, cy + 20, edges[0].get("label", "X →"), fill=COLORS["mid_gray"], size=12)
        svg += _svg_text(cx + 20, cy - qh + 10, edges[1].get("label", "Y ↑"), fill=COLORS["mid_gray"], size=12, anchor="start")

    # Plot nodes in quadrants
    quadrant_positions = [
        (cx - qw / 2, cy - qh / 2),  # top-left
        (cx + qw / 2, cy - qh / 2),  # top-right
        (cx - qw / 2, cy + qh / 2),  # bottom-left
        (cx + qw / 2, cy + qh / 2),  # bottom-right
    ]

    for i, node in enumerate(nodes[:4]):
        qx, qy = quadrant_positions[i % 4]
        colors = NODE_COLORS.get(node.get("type", "neutral"), NODE_COLORS["neutral"])
        rw, rh = 120, 40
        svg += _svg_rounded_rect(qx - rw / 2, qy - rh / 2, rw, rh, colors["fill"], colors["stroke"])
        svg += _svg_text(qx, qy + 5, node["label"], fill=colors["text"], size=12, bold=True)

    svg += _svg_footer()
    return svg


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

DIAGRAM_GENERATORS = {
    "flow": _generate_flow,
    "before_after": _generate_before_after,
    "layers": _generate_layers,
    "matrix": _generate_matrix,
}


def generate_dynamics_diagram(
    diagram_type: str = "flow",
    title: str = "",
    nodes: list[dict] | None = None,
    edges: list[dict] | None = None,
    output_path: str = "",
    width: int = 960,
    height: int = 760,
    show_edge_labels: bool = True,
) -> str:
    """力学ダイアグラムSVGを生成する

    Args:
        diagram_type: "flow", "before_after", "layers", "matrix"
        title: ダイアグラムのタイトル
        nodes: ノードリスト [{"id": str, "label": str, "type": str}, ...]
        edges: エッジリスト [{"from": str, "to": str, "label": str, "type": str}, ...]
        output_path: SVGファイルの出力先（空文字列の場合はファイル保存しない）
        width: SVG幅（px）
        height: SVG高さ（px）
        show_edge_labels: Falseにすると矢印ラベルを非表示（交差が多い複雑な図向け）

    Returns:
        SVG文字列
    """
    nodes = nodes or []
    # show_edge_labels=False の場合はラベルを除去
    edges_input = edges or []
    if not show_edge_labels:
        edges_input = [{k: v for k, v in e.items() if k != "label"} for e in edges_input]

    generator = DIAGRAM_GENERATORS.get(diagram_type)
    if not generator:
        raise ValueError(f"Unknown diagram type: {diagram_type}. Use: {list(DIAGRAM_GENERATORS.keys())}")

    svg = generator(title, nodes, edges_input, width, height)

    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(svg, encoding="utf-8")
        print(f"OK: Diagram saved to {output_path}")

    return svg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    # Demo: generate a sample flow diagram
    sample_svg = generate_dynamics_diagram(
        diagram_type="flow",
        title="プラットフォーム支配 × 規制の捕獲",
        nodes=[
            {"id": "apple", "label": "Apple\\n(App Store)", "type": "power"},
            {"id": "devs", "label": "開発者\\n(200万人)", "type": "affected"},
            {"id": "eu", "label": "EU\\n(DMA)", "type": "regulator"},
        ],
        edges=[
            {"from": "apple", "to": "devs", "label": "30%手数料", "type": "dominance"},
            {"from": "apple", "to": "eu", "label": "ロビイング", "type": "capture"},
            {"from": "eu", "to": "apple", "label": "制裁金€1.8B", "type": "regulation"},
        ],
        output_path="scripts/sample_diagram.svg",
    )
    print(f"Generated SVG ({len(sample_svg)} chars)")
    print("Open scripts/sample_diagram.svg in a browser to view.")
