"""Simulateur : un robot rebondit dans une piece 5 x 4.5 m avec odometrie bruitee.
Sert a tester mapper_core sans robot : python simulate.py  -> ecrit sim_map.png
"""
import math
import random
import sys

from mapper_core import OccupancyMap

ROOM = (-300.0, -2200.0, 4700.0, 2300.0)  # xmin, ymin, xmax, ymax (mm) ; base contre le mur x=-300
R = 170.0


def run(seconds=900, seed=1, gyro_drift_dps=0.05, out="sim_map.png"):
    rnd = random.Random(seed)
    m = OccupancyMap()
    x = y = 0.0
    th = 0.0           # vrai cap
    est_th = 0.0       # cap estime (derive)
    ex = ey = 0.0
    speed = 300.0      # mm/s
    dt = 0.1
    t = 0.0
    turn_left = 0.0
    m.add_pose(0, 0, 0)
    while t < seconds:
        if turn_left > 0:
            w = math.radians(120) * dt
            th += w
            est_th += w * (1 + rnd.gauss(0, 0.02))
            turn_left -= w
        else:
            nx = x + speed * dt * math.cos(th)
            ny = y + speed * dt * math.sin(th)
            fx = nx + R * math.cos(th)
            fy = ny + R * math.sin(th)
            if not (ROOM[0] < fx < ROOM[2] and ROOM[1] < fy < ROOM[3]):
                # contact : pare-chocs complet si presque perpendiculaire au mur
                if fx >= ROOM[2]:
                    wall_dir = 0.0
                elif fx <= ROOM[0]:
                    wall_dir = math.pi
                elif fy >= ROOM[3]:
                    wall_dir = math.pi / 2
                else:
                    wall_dir = -math.pi / 2
                diff = (th - wall_dir + math.pi) % (2 * math.pi) - math.pi
                if abs(diff) < math.radians(10):
                    # approche perpendiculaire : les deux pare-chocs touchent, le robot s'aligne
                    th = wall_dir
                    m.add_bump(ex, ey, math.degrees(est_th), 3)
                    nearest = round(est_th / (math.pi / 2)) * (math.pi / 2)
                    if abs(est_th - nearest) < math.radians(20):
                        est_th = nearest
                else:
                    m.add_bump(ex, ey, math.degrees(est_th), 2 if diff > 0 else 1)
                turn_left = math.radians(rnd.uniform(90, 200))
            else:
                x, y = nx, ny
                d = speed * dt * (1 + rnd.gauss(0, 0.01))
                ex += d * math.cos(est_th)
                ey += d * math.sin(est_th)
        est_th += math.radians(gyro_drift_dps) * dt
        m.add_pose(ex, ey, math.degrees(est_th))
        t += dt
    png = m.render_png(robot=(ex, ey, math.degrees(est_th)))
    with open(out, "wb") as f:
        f.write(png)
    return m


if __name__ == "__main__":
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 900
    m = run(seconds)
    print("stats:", m.coverage_stats())
    b = m.room_bounds()
    print("bounds estimees (mm):", b, "| vrai:", (-300 + 0, -2200, 4700, 2300))
