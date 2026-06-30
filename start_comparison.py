import glob
import os
import re
import subprocess
import sys


SCRIPTS_A_EXECUTER = [
    ("Capture peripheriques", "periph_tab_test.py"),
    ("Capture systeme", "system_tab_test.py"),
]

SCRIPT_COMPARAISON = "compare_photos_v3_.py"
PATTERN_DOSSIER_CAPTURE = re.compile(r"^\d+-")


def lancer_script(label, nom_script):
    print("\n" + "=" * 60)
    print(f"[+] {label} : lancement de {nom_script}")
    print("=" * 60)

    chemin_script = os.path.join(os.path.dirname(__file__), nom_script)
    resultat = subprocess.run([sys.executable, chemin_script])

    if resultat.returncode != 0:
        print(f"\n[-] Arret : {nom_script} a echoue avec le code {resultat.returncode}.")
        sys.exit(resultat.returncode)


def dossiers_avec_comparaison_possible():
    dossier_racine = os.path.dirname(__file__)
    dossiers = []

    for nom in os.listdir(dossier_racine):
        chemin_dossier = os.path.join(dossier_racine, nom)
        if not os.path.isdir(chemin_dossier) or not PATTERN_DOSSIER_CAPTURE.match(nom):
            continue

        captures = glob.glob(os.path.join(chemin_dossier, "capture_*.png"))
        if len(captures) >= 2:
            dossiers.append(nom)

    return dossiers


def main():
    print("[+] Demarrage du parcours complet.")

    for label, nom_script in SCRIPTS_A_EXECUTER:
        lancer_script(label, nom_script)

    dossiers_comparables = dossiers_avec_comparaison_possible()

    if not dossiers_comparables:
        print("\n[=] Comparaison ignoree : aucun dossier avec au moins 2 captures.")
        print("[+] Parcours termine.")
        return

    print("\n[+] Dossiers comparables detectes :")
    for nom in dossiers_comparables:
        print(f"    - {nom}")

    lancer_script("Comparaison visuelle", SCRIPT_COMPARAISON)
    print("\n[+] Parcours complet termine.")


if __name__ == "__main__":
    main()
