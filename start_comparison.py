import os
import subprocess
import sys
from config_loader import charger_config, chemin_dossier_run


SCRIPTS_A_EXECUTER = [
    ("Capture peripheriques", "periph_tab_test.py"),
    ("Capture systeme", "system_tab_test.py"),
]

SCRIPT_COMPARAISON = "compare_photos_v3_.py"


def lancer_script(label, nom_script):
    print("\n" + "=" * 60)
    print(f"[+] {label} : lancement de {nom_script}")
    print("=" * 60)

    chemin_script = os.path.join(os.path.dirname(__file__), nom_script)
    resultat = subprocess.run([sys.executable, chemin_script])

    if resultat.returncode != 0:
        print(f"\n[-] Arret : {nom_script} a echoue avec le code {resultat.returncode}.")
        sys.exit(resultat.returncode)


def comparaison_configuree(config):
    config_comparaison = config["comparison"]
    return bool(config_comparaison["reference_folder"] and config_comparaison["candidate_folder"])


def main():
    config = charger_config()
    dossier_run = chemin_dossier_run(config)

    print("[+] Demarrage du parcours complet.")
    print(f"[+] Dossier de captures : {dossier_run}")

    for label, nom_script in SCRIPTS_A_EXECUTER:
        lancer_script(label, nom_script)

    if not comparaison_configuree(config):
        print("\n[=] Comparaison ignoree : reference_folder/candidate_folder non renseignes.")
        print("[+] Parcours termine.")
        return

    lancer_script("Comparaison visuelle", SCRIPT_COMPARAISON)
    print("\n[+] Parcours complet termine.")


if __name__ == "__main__":
    main()
