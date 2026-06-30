import cv2
import glob
import os
import re
import sys
import numpy as np
from skimage.metrics import structural_similarity as ssim
from config_loader import charger_config, resoudre_chemin_config


# ========================================================
# CONFIGURATION ET CHOIX DE L'ALGORITHME
# ========================================================
config = charger_config()
config_comparaison = config["comparison"]

# Choix possibles : "OPENCV" (strict + recalage) ou "SSIM" (analyse de formes/structures)
ALGO_COMPARAISON = config_comparaison["algorithm"]

# Seuil de tolérance pour le mode SSIM (0.0 à 1.0)
# Plus on est proche de 1.0, plus on est strict. 0.95 est le parfait équilibre.
SEUIL_SSIM_TOLERANCE = config_comparaison["ssim_tolerance"]

nom_output = config_comparaison["output_filename"]
pattern_dossier = re.compile(r"^\d+-")
pattern_capture_timestamp = re.compile(r"^(?:(?P<libelle>.*)_)?(?P<timestamp>\d{2}-\d{2}-\d{4}_\d{2}h\d{2})$")
MAX_CORRECTION_DECALEUR = config_comparaison["max_alignment_shift"]


# Permet de surcharger l'algo via la ligne de commande (ex: python script.py opencv)
if len(sys.argv) > 1:
    choix_arg = sys.argv[1].upper()
    if choix_arg in ["OPENCV", "SSIM"]:
        ALGO_COMPARAISON = choix_arg
        print(f"[⚙️] Mode modifié par argument : {ALGO_COMPARAISON}\n")


def imread_unicode(chemin_fichier):
    try:
        format_brut = np.fromfile(chemin_fichier, dtype=np.uint8)
        return cv2.imdecode(format_brut, cv2.IMREAD_COLOR)
    except Exception:
        return None


def realigner_images(src_img, target_img):
    """Recale l'image cible si elle a glissé de quelques pixels (Utile pour OpenCV)"""
    g1 = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g2 = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    shift, _ = cv2.phaseCorrelate(g1, g2)
    shift_x, shift_y = shift[0], shift[1]

    if (0.5 < abs(shift_x) <= MAX_CORRECTION_DECALEUR) or (0.5 < abs(shift_y) <= MAX_CORRECTION_DECALEUR):
        print(f"   [🔧] Ajustement de l'alignement : X={shift_x:.1f}px, Y={shift_y:.1f}px")
        M = np.float32([[1, 0, -shift_x], [0, 1, -shift_y]])
        return cv2.warpAffine(target_img, M, (target_img.shape[1], target_img.shape[0]), borderMode=cv2.BORDER_REPLICATE)
    return target_img


def libelle_capture(chemin_capture):
    nom_fichier = os.path.splitext(os.path.basename(chemin_capture))[0]
    if not nom_fichier.startswith("capture_"):
        return None

    suffixe = nom_fichier[len("capture_"):]
    match_timestamp = pattern_capture_timestamp.match(suffixe)
    if match_timestamp:
        return match_timestamp.group("libelle") or "principal"
    return suffixe


def captures_par_libelle(chemin_dossier):
    captures = {}
    for chemin_capture in glob.glob(os.path.join(chemin_dossier, "capture_*.png")):
        libelle = libelle_capture(chemin_capture)
        if not libelle:
            continue

        capture_existante = captures.get(libelle)
        if not capture_existante or os.path.getmtime(chemin_capture) > os.path.getmtime(capture_existante):
            captures[libelle] = chemin_capture

    return captures


def dossiers_cibles(chemin_racine):
    if not os.path.isdir(chemin_racine):
        return set()

    return {
        nom
        for nom in os.listdir(chemin_racine)
        if os.path.isdir(os.path.join(chemin_racine, nom)) and pattern_dossier.match(nom)
    }


def comparer_images(chemin_reference, chemin_candidate):
    img1 = imread_unicode(chemin_reference)
    img2 = imread_unicode(chemin_candidate)

    if img1 is None or img2 is None or img1.shape != img2.shape:
        return None, 0, None

    image_resultat = img2.copy()
    compteur_diffs = 0
    score = None

    # ----------------------------------------------------
    # ANALYSE OPTION 1 : OPENCV (Pixel-à-Pixel strict)
    # ----------------------------------------------------
    if ALGO_COMPARAISON == "OPENCV":
        img2 = realigner_images(img1, img2)
        gris1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gris2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gris1, gris2)
        _, seuil = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        kernel = np.ones((5, 5), np.uint8)
        seuil_dilate = cv2.dilate(seuil, kernel, iterations=2)
        contours, _ = cv2.findContours(seuil_dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            if cv2.contourArea(c) < 35:
                continue
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(image_resultat, (x, y), (x + w, y + h), (0, 0, 255), 2)
            compteur_diffs += 1

    # ----------------------------------------------------
    # ANALYSE OPTION 2 : SSIM (Structural Similarity)
    # ----------------------------------------------------
    elif ALGO_COMPARAISON == "SSIM":
        gris1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gris2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        score, diff_map = ssim(gris1, gris2, full=True)
        diff_map = ((1 - diff_map) * 127.5).astype(np.uint8)
        _, seuil = cv2.threshold(diff_map, int((1 - SEUIL_SSIM_TOLERANCE) * 255), 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(seuil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            if cv2.contourArea(c) < 50:
                continue
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(image_resultat, (x, y), (x + w, y + h), (255, 0, 0), 2)
            compteur_diffs += 1

    return image_resultat, compteur_diffs, score


def enregistrer_resultat(image_resultat, chemin_output, compteur_diffs):
    texte = f"[{ALGO_COMPARAISON}] Modifs: {compteur_diffs}"
    couleur = (0, 0, 255) if ALGO_COMPARAISON == "OPENCV" else (255, 0, 0)
    cv2.putText(image_resultat, texte, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, couleur, 2)

    os.makedirs(os.path.dirname(chemin_output), exist_ok=True)
    _, extension = os.path.splitext(chemin_output)
    succes, extension_encodee = cv2.imencode(extension, image_resultat)
    if succes:
        extension_encodee.tofile(chemin_output)
        return True
    return False


def main():
    dossier_reference = resoudre_chemin_config(config_comparaison["reference_folder"])
    dossier_candidate = resoudre_chemin_config(config_comparaison["candidate_folder"])

    if not dossier_reference or not dossier_candidate:
        print("[=] Comparaison ignoree : reference_folder/candidate_folder non renseignes.")
        return

    if not os.path.isdir(dossier_reference) or not os.path.isdir(dossier_candidate):
        print("[-] Comparaison impossible : un des dossiers configures est introuvable.")
        print(f"    reference_folder: {dossier_reference}")
        print(f"    candidate_folder: {dossier_candidate}")
        return

    dossier_resultats = resoudre_chemin_config(config_comparaison["results_folder"])
    print(f"[+] Comparaison reference : {dossier_reference}")
    print(f"[+] Comparaison candidate : {dossier_candidate}")
    print(f"[⚙️] Mode de comparaison sélectionné : {ALGO_COMPARAISON}\n")

    dossiers_communs = sorted(dossiers_cibles(dossier_reference) & dossiers_cibles(dossier_candidate))
    if not dossiers_communs:
        print("[-] Aucun dossier typé 'chiffre-' commun aux deux dossiers sélectionnés.")
        return

    total_comparaisons = 0
    total_differences = 0

    for nom_dossier in dossiers_communs:
        print(f"\n📁 Traitement du dossier : {nom_dossier}")
        chemin_reference = os.path.join(dossier_reference, nom_dossier)
        chemin_candidate = os.path.join(dossier_candidate, nom_dossier)
        captures_reference = captures_par_libelle(chemin_reference)
        captures_candidate = captures_par_libelle(chemin_candidate)

        libelles_communs = sorted(set(captures_reference) & set(captures_candidate))
        if not libelles_communs:
            print("   [-] Ignoré : aucune capture comparable.")
            continue

        for libelle in libelles_communs:
            chemin_capture_reference = captures_reference[libelle]
            chemin_capture_candidate = captures_candidate[libelle]
            image_resultat, compteur_diffs, score = comparer_images(chemin_capture_reference, chemin_capture_candidate)
            total_comparaisons += 1

            if image_resultat is None:
                print(f"   [-] {libelle} : dimensions incohérentes ou fichiers corrompus.")
                continue

            if score is not None:
                print(f"   [📊] {libelle} : score SSIM {score * 100:.2f}%")

            if compteur_diffs > 0:
                nom_sortie = f"{os.path.splitext(nom_output)[0]}_{libelle}.png"
                chemin_output = os.path.join(dossier_resultats, nom_dossier, nom_sortie)
                if enregistrer_resultat(image_resultat, chemin_output, compteur_diffs):
                    total_differences += compteur_diffs
                    print(f"   [+] {libelle} -> {chemin_output} ({compteur_diffs} zones repérées)")
            else:
                print(f"   [=] {libelle} : RAS")

    print("\n" + "=" * 60)
    print(f"[+] Comparaisons effectuées : {total_comparaisons}")
    print(f"[+] Zones de différence repérées : {total_differences}")
    print("[+] Traitement global terminé avec succès !")


if __name__ == "__main__":
    main()
