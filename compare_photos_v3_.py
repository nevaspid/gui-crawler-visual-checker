import cv2
import numpy as np
import sys
import os
import glob
import re
from skimage.metrics import structural_similarity as ssim

# ========================================================
# CONFIGURATION ET CHOIX DE L'ALGORITHME
# ========================================================
# Choix possibles : "OPENCV" (strict + recalage) ou "SSIM" (analyse de formes/structures)
ALGO_COMPARAISON = "OPENCV" 

# Seuil de tolérance pour le mode SSIM (0.0 à 1.0)
# Plus on est proche de 1.0, plus on est strict. 0.95 est le parfait équilibre.
SEUIL_SSIM_TOLERANCE = 0.95 

nom_output = "differences_visuelles.png"
pattern_dossier = re.compile(r"^\d+-")
MAX_CORRECTION_DECALEUR = 5 

dossier_racine = os.getcwd()
print(f"[+] Scan des dossiers depuis la racine : {dossier_racine}")
print(f"[⚙️] Mode de comparaison sélectionné : {ALGO_COMPARAISON}\n")

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

elements = os.listdir(dossier_racine)
dossiers_cibles = [e for e in elements if os.path.isdir(e) and pattern_dossier.match(e)]

if not dossiers_cibles:
    print("[-] Aucun dossier typé 'chiffre-' détecté à la racine.")
    sys.exit(0)

for nom_dossier in dossiers_cibles:
    print(f"\n📁 Traitement du dossier : {nom_dossier}")
    
    chemin_recherche = os.path.join(nom_dossier, "capture_*.png")
    fichiers = glob.glob(chemin_recherche)
    fichiers.sort(key=os.path.getmtime)
    
    if len(fichiers) < 2:
        print(f"   [-] Ignoré : Moins de 2 captures présentes.")
        continue
        
    img1 = imread_unicode(fichiers[-2])
    img2 = imread_unicode(fichiers[-1])
    
    if img1 is None or img2 is None or img1.shape != img2.shape:
        print("   [-] Erreur : Dimensions incohérentes ou fichiers corrompus.")
        continue
        
    image_resultat = img2.copy()
    compteur_diffs = 0
    
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
        
        # Le paramètre full=True génère une carte complète des différences structurelles
        score, diff_map = ssim(gris1, gris2, full=True)
        
        # diff_map est compris entre -1 et 1. On le convertit en image classique (0-255)
        diff_map = ((1 - diff_map) * 127.5).astype(np.uint8)
        
        # On seuille pour isoler uniquement les zones qui décrochent du score cible
        _, seuil = cv2.threshold(diff_map, int((1 - SEUIL_SSIM_TOLERANCE) * 255), 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(seuil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for c in contours:
            # Le SSIM étant plus large, on ignore les contours de moins de 50 pixels de surface
            if cv2.contourArea(c) < 50:
                continue
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(image_resultat, (x, y), (x + w, y + h), (255, 0, 0), 2) # Bleu pour le SSIM
            compteur_diffs += 1
            
        print(f"   [📊] Score de similarité globale SSIM : {score * 100:.2f}%")

    # ----------------------------------------------------
    # ENREGISTREMENT DES RÉSULTATS
    # ----------------------------------------------------
    chemin_final_output = os.path.join(nom_dossier, nom_output)
    
    if compteur_diffs > 0:
        texte = f"[{ALGO_COMPARAISON}] Modifs: {compteur_diffs}"
        couleur = (0, 0, 255) if ALGO_COMPARAISON == "OPENCV" else (255, 0, 0)
        cv2.putText(image_resultat, texte, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, couleur, 2)
        
        _, extension = os.path.splitext(chemin_final_output)
        succes, extension_encodee = cv2.imencode(extension, image_resultat)
        if succes:
            extension_encodee.tofile(chemin_final_output)
            print(f"   [+] Fichier généré -> {nom_output} ({compteur_diffs} zones repérées)")
    else:
        print(f"   [=] RAS : Aucun changement structurel ou pixel significatif.")

print("\n" + "="*60)
print("[+] Traitement global terminé avec succès !")