import json
import os


CONFIG_FILENAME = "config.json"


def charger_config():
    chemin_config = os.path.join(os.path.dirname(__file__), CONFIG_FILENAME)
    with open(chemin_config, "r", encoding="utf-8") as fichier:
        return json.load(fichier)


def dossier_projet():
    return os.path.dirname(__file__)


def chemin_dossier_run(config):
    nom_dossier = f"green{config['run']['version_config_file']}"
    return os.path.join(dossier_projet(), nom_dossier)


def resoudre_chemin_config(chemin):
    if not chemin:
        return ""
    if os.path.isabs(chemin):
        return chemin
    return os.path.join(dossier_projet(), chemin)
