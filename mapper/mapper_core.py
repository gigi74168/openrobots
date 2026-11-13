"""Coeur du mapper Aerobot : grille d'occupation + rendu PNG.

Aucune dependance Home Assistant : utilise uniquement la lib standard + Pillow.
Unites : mm et degres. Repere : origine = base, x avant du robot sur la base,
y gauche, theta anti-horaire (identique au firmware).

Modele :
  - cellules "visitees" : zone balayee par le robot (empreinte circulaire) le long de la trajectoire
  - cellules "obstacle" : points de contact des pare-chocs (murs, meubles)
"""
from __future__ import annotations

import io
import json
import math
import os
from collections import deque
from typing import Deque, Dict, Optional, Tuple

from PIL import Image, ImageDraw

CELL_MM = 50                # taille d'une cellule
ROBOT_RADIUS_MM = 170       # rayon du Roomba (~34 cm de diametre)
SWEEP_RADIUS_MM = 140       # zone consideree "passee" autour du centre
BUMP_FRONT_MM = 170         # distance centre -> pare-chocs
BUMP_LATERAL_MM = 90        # decalage lateral pour un contact gauche/droit seul

# couleurs
C_UNKNOWN = (38, 42, 50)
C_VISITED = (196, 214, 228)
C_VISITED_MULTI = (150, 188, 214)
C_WALL = (20, 22, 26)
C_WALL_SOFT = (230, 90, 70)
C_TRAIL = (60, 120, 200)
C_ROBOT = (46, 160, 90)
C_DOCK = (240, 190, 40)
C_ROOM = (240, 240, 240)


def _cell(v_mm: float) -> int:
    return int(math.floor(v_mm / CELL_MM))


class OccupancyMap:
    WALL_TOL_MM = 350

    def __init__(self) -> None:
        self.visited: Dict[Tuple[int, int], int] = {}
        self.hits: Dict[Tuple[int, int], int] = {}
        self.flat_hits: Dict[Tuple[int, int], int] = {}
        self.offset = [0.0, 0.0]               # correction de position apprise sur les murs
        self.lines: Dict[int, list] = {}       # murs connus par direction (0:+x 1:+y 2:-x 3:-y)
        self.trail: Deque[Tuple[float, float]] = deque(maxlen=4000)
        self.last_pose: Optional[Tuple[float, float, float]] = None
        self.dirty = True
        self._disc = self._make_disc(SWEEP_RADIUS_MM)

    @staticmethod
    def _make_disc(r_mm: float):
        r = int(math.ceil(r_mm / CELL_MM))
        out = []
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if (dx * CELL_MM) ** 2 + (dy * CELL_MM) ** 2 <= r_mm ** 2:
                    out.append((dx, dy))
        return out

    # ------------------------------------------------------------------ entree
    def notify_docked(self) -> None:
        """Le firmware remet la pose a zero sur la base : la correction du mapper repart de zero."""
        self.offset = [0.0, 0.0]

    def _match_wall(self, x: float, y: float, theta_deg: float) -> None:
        """Contact plat (cap recale sur 0/90/180/270) : cale la position sur les murs deja connus.
        Un mur n'est utilise comme reference qu'apres >= 2 contacts concordants (evite les meubles)."""
        k = int(round(theta_deg / 90.0)) % 4
        if abs(((theta_deg - k * 90.0 + 180.0) % 360.0) - 180.0) > 12.0:
            return
        th = math.radians(k * 90.0)
        px = x + BUMP_FRONT_MM * math.cos(th)
        py = y + BUMP_FRONT_MM * math.sin(th)
        c = px if k in (0, 2) else py          # coordonnee du mur le long de l'axe de marche
        lines = self.lines.setdefault(k, [])
        for ln in lines:
            if abs(ln[0] - c) < self.WALL_TOL_MM:
                if ln[1] >= 2:
                    err = ln[0] - c
                    self.offset[0 if k in (0, 2) else 1] += err * 0.7
                    c = c + err * 0.7
                ln[0] = (ln[0] * ln[1] + c) / (ln[1] + 1)
                ln[1] += 1
                return
        lines.append([c, 1])

    def add_pose(self, x: float, y: float, theta_deg: float) -> None:
        x += self.offset[0]
        y += self.offset[1]
        if self.last_pose is not None:
            lx, ly, _ = self.last_pose
            dist = math.hypot(x - lx, y - ly)
            if dist > 1500:           # saut (reset de pose a la base) : ne pas tracer de ligne
                self.last_pose = None
        if self.last_pose is None:
            self._stamp(x, y)
        else:
            lx, ly, _ = self.last_pose
            dist = math.hypot(x - lx, y - ly)
            steps = max(1, int(dist / (CELL_MM / 2)))
            for i in range(1, steps + 1):
                t = i / steps
                self._stamp(lx + (x - lx) * t, ly + (y - ly) * t)
        self.trail.append((x, y))
        self.last_pose = (x, y, theta_deg)
        self.dirty = True

    def _stamp(self, x: float, y: float) -> None:
        cx, cy = _cell(x), _cell(y)
        for dx, dy in self._disc:
            k = (cx + dx, cy + dy)
            self.visited[k] = self.visited.get(k, 0) + 1

    def bump_point(self, x: float, y: float, theta_deg: float, side: int) -> Tuple[float, float]:
        """side : bit0 = pare-chocs droit, bit1 = gauche."""
        th = math.radians(theta_deg)
        if side == 1:
            lat = -BUMP_LATERAL_MM
        elif side == 2:
            lat = BUMP_LATERAL_MM
        else:
            lat = 0.0
        fx = BUMP_FRONT_MM * math.cos(th) - lat * math.sin(th)
        fy = BUMP_FRONT_MM * math.sin(th) + lat * math.cos(th)
        return x + fx, y + fy

    def add_bump(self, x: float, y: float, theta_deg: float, side: int) -> None:
        x += self.offset[0]
        y += self.offset[1]
        if side == 3:
            before = tuple(self.offset)
            self._match_wall(x, y, theta_deg)
            x += self.offset[0] - before[0]
            y += self.offset[1] - before[1]
        px, py = self.bump_point(x, y, theta_deg, side)
        k = (_cell(px), _cell(py))
        self.hits[k] = self.hits.get(k, 0) + 1
        if side == 3:   # contact complet : cap recale par le firmware, point fiable
            self.flat_hits[k] = self.flat_hits.get(k, 0) + 1
            th = math.radians(theta_deg)
            for lat in (-BUMP_LATERAL_MM, BUMP_LATERAL_MM):
                qx = px - lat * math.sin(th)
                qy = py + lat * math.cos(th)
                k2 = (_cell(qx), _cell(qy))
                self.hits[k2] = self.hits.get(k2, 0) + 1
        self.dirty = True

    # --------------------------------------------------------------- analyse
    def room_bounds(self, min_points: int = 12) -> Optional[Tuple[float, float, float, float]]:
        """Estimation du rectangle de la piece (xmin, ymin, xmax, ymax) en mm a partir des
        contacts et de la zone balayee. None tant qu'il y a trop peu de donnees."""
        # 1) murs confirmes par contacts plats repetes (le plus fiable)
        best = {}
        for k in range(4):
            cand = [ln for ln in self.lines.get(k, []) if ln[1] >= 2]
            if cand:
                best[k] = max(cand, key=lambda ln: ln[1])[0]
        if len(best) == 4:
            return best[2], best[3], best[0], best[1]
        # 2) sinon on prefere les contacts "plats" (cap recale sur un mur) ; sinon tous les contacts
        src = self.flat_hits if len(self.flat_hits) >= min_points else self.hits
        pts = list(src.keys())
        if len(pts) < min_points:
            return None
        xs = sorted(p[0] for p in pts)
        ys = sorted(p[1] for p in pts)
        lo = int(len(xs) * 0.05)
        hi = max(lo, int(len(xs) * 0.95) - 1)
        xmin, xmax = xs[lo] * CELL_MM, (xs[hi] + 1) * CELL_MM
        lo = int(len(ys) * 0.05)
        hi = max(lo, int(len(ys) * 0.95) - 1)
        ymin, ymax = ys[lo] * CELL_MM, (ys[hi] + 1) * CELL_MM
        return xmin, ymin, xmax, ymax

    def coverage_stats(self) -> Dict[str, float]:
        area_m2 = len(self.visited) * (CELL_MM / 1000.0) ** 2
        b = self.room_bounds()
        room = 0.0
        if b:
            room = (b[2] - b[0]) * (b[3] - b[1]) / 1e6
        return {"visited_m2": round(area_m2, 2), "room_m2": round(room, 2),
                "coverage_pct": round(min(100.0, 100.0 * area_m2 / room), 1) if room > 0 else 0.0}

    # ----------------------------------------------------------------- rendu
    def render_png(self, px_per_cell: int = 6, margin_cells: int = 8,
                   robot: Optional[Tuple[float, float, float]] = None) -> bytes:
        keys = list(self.visited.keys()) + list(self.hits.keys())
        keys.append((0, 0))
        if robot:
            keys.append((_cell(robot[0]), _cell(robot[1])))
        minx = min(k[0] for k in keys) - margin_cells
        maxx = max(k[0] for k in keys) + margin_cells
        miny = min(k[1] for k in keys) - margin_cells
        maxy = max(k[1] for k in keys) + margin_cells
        w, h = maxx - minx + 1, maxy - miny + 1
        # largeur mini pour que l'image ne soit pas minuscule
        w_img, h_img = max(w, 60) , max(h, 60)
        ox = (w_img - w) // 2
        oy = (h_img - h) // 2

        img = Image.new("RGB", (w_img * px_per_cell, h_img * px_per_cell), C_UNKNOWN)
        d = ImageDraw.Draw(img)

        def to_px(xmm: float, ymm: float) -> Tuple[float, float]:
            # y vers le haut -> pixel y vers le bas
            cxf = xmm / CELL_MM - minx + ox
            cyf = (maxy - ymm / CELL_MM) + oy
            return cxf * px_per_cell, cyf * px_per_cell

        def cell_rect(cx: int, cy: int) -> Tuple[float, float, float, float]:
            x0 = (cx - minx + ox) * px_per_cell
            y1 = (maxy - cy + 1 + oy) * px_per_cell - px_per_cell
            return x0, y1, x0 + px_per_cell - 1, y1 + px_per_cell - 1

        for (cx, cy), n in self.visited.items():
            d.rectangle(cell_rect(cx, cy), fill=C_VISITED_MULTI if n > 6 else C_VISITED)

        b = self.room_bounds()
        if b:
            x0, y0 = to_px(b[0], b[3])
            x1, y1 = to_px(b[2], b[1])
            d.rectangle((x0, y0, x1, y1), outline=C_ROOM, width=1)

        for (cx, cy), n in self.hits.items():
            d.rectangle(cell_rect(cx, cy), fill=C_WALL if n >= 2 else C_WALL_SOFT)

        if len(self.trail) > 1:
            pts = [to_px(x, y) for x, y in list(self.trail)[-1500:]]
            d.line(pts, fill=C_TRAIL, width=1)

        # base
        bx, by = to_px(0, 0)
        r = 5
        d.rectangle((bx - r, by - r, bx + r, by + r), outline=C_DOCK, width=2)

        # robot
        rp = robot or self.last_pose
        if rp:
            rx, ry = to_px(rp[0], rp[1])
            rr = ROBOT_RADIUS_MM / CELL_MM * px_per_cell
            d.ellipse((rx - rr, ry - rr, rx + rr, ry + rr), outline=C_ROBOT, width=2)
            th = math.radians(rp[2])
            d.line((rx, ry, rx + rr * math.cos(th), ry - rr * math.sin(th)), fill=C_ROBOT, width=3)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    # ------------------------------------------------------------ persistance
    def save(self, path: str) -> None:
        data = {
            "visited": [[k[0], k[1], v] for k, v in self.visited.items()],
            "hits": [[k[0], k[1], v] for k, v in self.hits.items()],
            "trail": list(self.trail)[-1500:],
        }
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)

    def load(self, path: str) -> bool:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return False
        self.visited = {(a, b): c for a, b, c in data.get("visited", [])}
        self.hits = {(a, b): c for a, b, c in data.get("hits", [])}
        self.trail = deque((tuple(p) for p in data.get("trail", [])), maxlen=4000)
        self.dirty = True
        return True

    def reset(self) -> None:
        self.visited.clear()
        self.hits.clear()
        self.flat_hits.clear()
        self.offset = [0.0, 0.0]
        self.lines.clear()
        self.trail.clear()
        self.last_pose = None
        self.dirty = True
