#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import zipfile
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = BASE_DIR
OUT_NAME = "tomato-vbook-ext.zip"
OUT_PATH = os.path.join(BASE_DIR, OUT_NAME)

def bump_version(plugin_json_path):
    try:
        with open(plugin_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        old_ver = data.get("metadata", {}).get("version", 0)
        new_ver = old_ver + 1
        data["metadata"]["version"] = new_ver
        with open(plugin_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[+] Version: {old_ver} -> {new_ver}")
        return True
    except Exception as e:
        print(f"[-] Khong the tang version: {e}")
        return False

def repack(auto_bump=True):
    plugin_json = os.path.join(SRC_DIR, "plugin.json")
    if auto_bump and os.path.exists(plugin_json):
        bump_version(plugin_json)

    if os.path.exists(OUT_PATH):
        os.remove(OUT_PATH)

    added = []
    with zipfile.ZipFile(OUT_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(SRC_DIR):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__"]]
            for fname in files:
                if fname.startswith(".") or fname.endswith(".zip") or fname == "repack_ext.py":
                    continue
                abs_path = os.path.join(root, fname)
                arc_name = os.path.relpath(abs_path, SRC_DIR).replace("\\", "/")
                zf.write(abs_path, arc_name)
                added.append(arc_name)

    print(f"\n[v] Dong goi thanh cong: {OUT_NAME}")

if __name__ == "__main__":
    repack()
