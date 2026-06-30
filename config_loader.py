import json
import os


CONFIG_FILENAME = "config.json"


def charger_config():
    chemin_config = os.path.join(os.path.dirname(__file__), CONFIG_FILENAME)
    with open(chemin_config, "r", encoding="utf-8") as fichier:
        return json.load(fichier)
