#!/usr/bin/env python3
"""Draw the architecture of the XDP per-source-IP rate limiter (xdp_pipeline.png).

Usage: python3 make_xdp_pipeline.py   (needs matplotlib)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xdp_pipeline.png")

C_USER = "#e8eef8"
C_KERN = "#f6f6f6"
C_XDP = "#fff1d6"
C_MAP = "#e3f2e6"
C_DROP = "#f9dcdc"
C_PASS = "#dceaf9"
EDGE = "#333333"

fig, ax = plt.subplots(figsize=(13, 9.0), dpi=160)
ax.set_xlim(0, 130)
ax.set_ylim(0, 92)
ax.axis("off")


def box(x, y, w, h, text, fc, fs=9, bold=False, ec=EDGE, lw=1.2, ls="-", align="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2",
                                fc=fc, ec=ec, lw=lw, ls=ls))
    ax.text(x + w / 2 if align == "center" else x + 1.2, y + h / 2, text, ha=align,
            va="center", fontsize=fs, fontweight="bold" if bold else "normal",
            family="DejaVu Sans")


def arrow(x1, y1, x2, y2, text=None, color=EDGE, ls="-", lw=1.5, tx=0, ty=0, fs=8, rad=0.0,
          style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13,
                                 color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((x1 + x2) / 2 + tx, (y1 + y2) / 2 + ty, text, fontsize=fs, color=color,
                ha="center", va="center",
                bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


# ---- regions --------------------------------------------------------------
ax.add_patch(FancyBboxPatch((1, 74), 128, 17, boxstyle="round,pad=0.2,rounding_size=1",
                            fc=C_USER, ec="#8aa2c8", lw=1))
ax.text(2.5, 89.3, "USER SPACE", fontsize=10, fontweight="bold", color="#3b5b8c")
ax.add_patch(FancyBboxPatch((1, 1), 128, 71, boxstyle="round,pad=0.2,rounding_size=1",
                            fc=C_KERN, ec="#aaaaaa", lw=1))
ax.text(2.5, 69.8, "KERNEL", fontsize=10, fontweight="bold", color="#555555")

# ---- user space -----------------------------------------------------------
box(4, 76.5, 36, 11,
    "xdp_ratelimit_user (libbpf skeleton)\nload + verify, write rl_config,\n"
    "fill allow/block lists, attach,\nprint stats & top sources every 1 s", "white", fs=8.2)
box(46, 76.5, 30, 11, "bpftool / ip link\nprog show, map dump,\nmap update (runtime config)",
    "white", fs=8.2)
box(82, 76.5, 44, 11, "IDS / ML classifier (Lab 3 model, Lab 4)\nflags malicious source IPs\n"
    "-> bpf_map_update_elem(rl_block, ip)", "white", fs=8.2, ls="--")

# ---- NIC + hook -----------------------------------------------------------
box(3, 32, 15, 14, "NIC\nRX ring\n(driver)", "#dddddd", fs=9, bold=True)
ax.text(10.5, 22.5, "packets in\n(attacker flood +\nbenign clients)", ha="center", fontsize=8)
arrow(10.5, 28, 10.5, 31.6)

ax.add_patch(FancyBboxPatch((23, 16), 54, 46, boxstyle="round,pad=0.3,rounding_size=1.5",
                            fc=C_XDP, ec="#d08a00", lw=2))
ax.text(50, 59.8, "XDP hook  -  SEC(\"xdp\") xdp_ratelimit()", ha="center", fontsize=10,
        fontweight="bold", color="#8a5a00")
ax.text(50, 57.0, "native: in the driver before any sk_buff exists;"
        " generic: after skb allocation", ha="center", fontsize=7.3, style="italic")
arrow(18.3, 39, 22.8, 39)

steps = [
    ("1  parse Ethernet -> [VLAN] -> IPv4", "non-IPv4 -> PASS"),
    ("2  saddr in rl_block ?", "yes -> DROP"),
    ("3  saddr in rl_allow ?", "yes -> PASS"),
    ("4  read rl_config (limit, window)", "limit 0 -> PASS"),
    ("5  rl_state[saddr]: window expired? reset\n    count++  (atomic, bpf_ktime_get_ns)", ""),
    ("6  count > limit ?", "yes -> DROP\nno  -> PASS"),
]
y = 54
for i, (s, side) in enumerate(steps):
    h = 6.4 if "\n" in s else 4.3
    box(26, y - h, 33, h, s, "white", fs=7.6, align="left")
    if side:
        ax.text(61, y - h / 2, side, fontsize=7.6, va="center", color="#7a4a00")
    if i < len(steps) - 1:
        arrow(42.5, y - h - 0.1, 42.5, y - h - 1.3, lw=1)
    y -= h + 1.4

# ---- maps -----------------------------------------------------------------
ax.add_patch(FancyBboxPatch((83, 29), 44, 38, boxstyle="round,pad=0.3,rounding_size=1.5",
                            fc="#f3faf4", ec="#2e6b3a", lw=1.2))
ax.text(105, 64.6, "BPF maps (shared kernel <-> user space)", ha="center", fontsize=9,
        fontweight="bold", color="#2e6b3a")
maps = [
    ("rl_config", "ARRAY[1]  {limit, window_ns}"),
    ("rl_state", "LRU_HASH 64k  saddr -> {win_start,\ncount, total, dropped}"),
    ("rl_stats", "PERCPU_ARRAY  pass / drop-rate /\ndrop-block / non-IPv4"),
    ("rl_allow", "HASH  saddr -> 1  (bypass limiter)"),
    ("rl_block", "HASH  saddr -> 1  (always drop)"),
]
my = 61.5
for name, desc in maps:
    h = 6.0 if "\n" in desc else 4.4
    box(85, my - h, 40, h, f"{name}: {desc}", C_MAP, fs=7.6, align="left")
    my -= h + 1.5
# program <-> maps
arrow(77.6, 41, 82.6, 41, lw=1.4, color="#2e6b3a", style="<|-|>")
ax.text(80.1, 45, "lookup\nupdate", fontsize=7, ha="center", color="#2e6b3a")

# user space <-> maps (bpf() syscalls)
arrow(22, 76.2, 92, 67.6, "bpf() syscalls: read rl_stats / rl_state, write config",
      color="#3b5b8c", ls="--", lw=1.2, ty=1.6, fs=7.5, style="<|-|>")
arrow(61, 76.2, 103, 67.6, color="#3b5b8c", ls="--", lw=1.2, style="<|-|>")
arrow(110, 76.2, 118, 67.6, "add IP to rl_block", color="#3b5b8c", ls="--", lw=1.2,
      tx=4, ty=0.5, fs=7.5)

# ---- verdicts -------------------------------------------------------------
box(27, 3, 26, 7, "XDP_DROP\nbuffer recycled - no skb,\nno netfilter, no socket cost",
    C_DROP, fs=7.6)
box(84, 3, 42, 9, "XDP_PASS -> sk_buff alloc -> tc ingress ->\nnetfilter (iptables/nft) -> "
    "IP/TCP/UDP\n-> sockets -> applications", C_PASS, fs=7.8)
arrow(40, 15.6, 40, 10.6, color="#b02a2a", lw=1.6)
arrow(77.6, 19, 83.6, 10, color="#2a5bb0", lw=1.6)

fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print("wrote", OUT)
