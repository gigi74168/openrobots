"""App AppDaemon : construit la carte Aerobot a partir des entites ESPHome et la publie
en PNG (base64) sur MQTT pour l'entite `image` MQTT de Home Assistant.

Installation (HA OS) : add-on "AppDaemon", puis
  - add-on > Configuration > python_packages : Pillow
  - copier ce fichier + mapper_core.py dans /addon_configs/a0d7b954_appdaemon/apps/
  - ajouter le bloc de apps.yaml (voir apps.yaml fourni)
"""
import base64
import os
import sys

import appdaemon.plugins.hass.hassapi as hass

sys.path.insert(0, os.path.dirname(__file__))
from mapper_core import OccupancyMap  # noqa: E402


class RoombaMap(hass.Hass):
    def initialize(self):
        p = self.args.get("prefix", "sensor.aerobot")
        self.e = {
            "x": f"{p}_pose_x",
            "y": f"{p}_pose_y",
            "th": f"{p}_pose_theta",
            "bc": f"{p}_collision_compteur",
            "bx": f"{p}_collision_x",
            "by": f"{p}_collision_y",
            "bth": f"{p}_collision_theta",
            "bs": f"{p}_collision_cote",
            "act": self.args.get("activity_entity", f"{p}_activite"),
        }
        self.topic = self.args.get("topic", "aerobot/map/png")
        self.stats_topic = self.args.get("stats_topic", "aerobot/map/stats")
        self.save_path = self.args.get("save_path", os.path.join(os.path.dirname(__file__), "aerobot_map.json"))
        self.reset_entity = self.args.get("reset_entity", "input_button.aerobot_reset_map")

        self.map = OccupancyMap()
        if self.map.load(self.save_path):
            self.log("Carte rechargee depuis le disque")
        self.last_bump_count = None
        self.was_docked = False
        self.last_publish = 0.0
        self.last_save = 0.0

        self.run_every(self.tick, "now", 0.5)
        self.listen_state(self.on_reset, self.reset_entity)

    # ------------------------------------------------------------------
    def _f(self, key):
        try:
            return float(self.get_state(self.e[key]))
        except (TypeError, ValueError):
            return None

    def on_reset(self, entity, attribute, old, new, kwargs):
        self.log("Reinitialisation de la carte")
        self.map.reset()
        self.publish(force=True)

    def tick(self, kwargs):
        act = self.get_state(self.e["act"])
        x, y, th = self._f("x"), self._f("y"), self._f("th")
        if None in (x, y, th):
            return
        docked = act in ("docked", "charging")
        if docked:
            if not self.was_docked:
                self.map.notify_docked()
            self.was_docked = True
        else:
            self.was_docked = False

        # collisions : on traite chaque increment du compteur
        bc = self._f("bc")
        if bc is not None:
            if self.last_bump_count is None:
                self.last_bump_count = bc
            elif bc != self.last_bump_count:
                bx, by, bth, bs = self._f("bx"), self._f("by"), self._f("bth"), self._f("bs")
                if None not in (bx, by, bth, bs):
                    self.map.add_bump(bx, by, bth, int(bs))
                self.last_bump_count = bc

        # trajectoire uniquement quand le robot est actif
        if act in ("cleaning", "returning", "manual", "idle") or docked:
            self.map.add_pose(x, y, th)

        self.publish()

    def publish(self, force=False):
        now = self.get_now_ts()
        if not (force or (self.map.dirty and now - self.last_publish >= 2.0)):
            return
        rp = None
        if self.map.last_pose:
            rp = self.map.last_pose
        png = self.map.render_png(robot=rp)
        self.call_service("mqtt/publish", topic=self.topic,
                          payload=base64.b64encode(png).decode("ascii"), retain=True)
        st = self.map.coverage_stats()
        self.call_service("mqtt/publish", topic=self.stats_topic,
                          payload=str(st).replace("'", '"'), retain=True)
        self.map.dirty = False
        self.last_publish = now
        if now - self.last_save > 60:
            try:
                self.map.save(self.save_path)
                self.last_save = now
            except OSError as exc:
                self.log(f"Sauvegarde impossible: {exc}", level="WARNING")
