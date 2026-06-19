"""Single source of truth for reading authored mod meta.xml files.

meta.xml is the optional WoT package manifest (World of Tanks: Mod Packages
spec). When present it holds the package <id>, <version>, <name>, and
<description>. All repository scripts read it through this helper so the
authored meta.xml stays the only source of these values.
"""

import os
import xml.etree.ElementTree as ET

from .paths import MODS_DIR


def meta_path_for(mod_name):
    return os.path.join(MODS_DIR, mod_name, "meta.xml")


def read_meta(mod_name):
    root = ET.parse(meta_path_for(mod_name)).getroot()
    return {
        "id": root.findtext("id", "").strip(),
        "version": root.findtext("version", "0.0.0.0").strip(),
        "name": root.findtext("name", "").strip(),
        "description": root.findtext("description", "").strip(),
    }
