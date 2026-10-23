#!/usr/bin/env python3
"""Fills the app icon fields of index-v1 from the metadata icons.

fdroidserver only sets index-v1's top-level "icon" (and fills repo/icons-*/) from icons it
extracts out of the APK, which doesn't work for adaptive vector icons. Clients that read
index-v1 (Droid-ify, Neo Store, older F-Droid) then show no icon, although the icon from
metadata/<applicationId>/en-US/icon.png is in index-v2. This copies that icon into the
icons-* directories and sets "icon" in index-v1.json.

Run between `fdroid update --nosign` and `fdroid signindex`.
"""
import json
import shutil
from pathlib import Path

REPO = Path("repo")
DENSITIES = ("icons", "icons-120", "icons-160", "icons-240", "icons-320", "icons-480", "icons-640")


def main():
    index_path = REPO / "index-v1.json"
    index = json.loads(index_path.read_text())
    for app in index["apps"]:
        if app.get("icon"):
            continue
        name = app.get("localized", {}).get("en-US", {}).get("icon")
        if not name:
            continue
        src = REPO / app["packageName"] / "en-US" / name
        icon = f'{app["packageName"]}.{app["suggestedVersionCode"]}.png'
        for d in DENSITIES:
            (REPO / d).mkdir(exist_ok=True)
            shutil.copyfile(src, REPO / d / icon)
        app["icon"] = icon
        print(f"v1 icon: {icon}")
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
