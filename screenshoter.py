import os
import time
import pyautogui
from PIL import ImageGrab
from config_loader import charger_config

def capture_depuis_souris():
    config = charger_config()
    largeur = config["capture"]["largeur_box"]
    hauteur = config["capture"]["hauteur_box"]
    
    print("Le script est lancé. Positionnez votre souris...")
    # Attente de 5 secondes
    for i in range(5, 0, -1):
        print(f"Capture dans {i} secondes...")
        time.sleep(1)
        
    # 1. Récupérer la position actuelle de la souris (le coin supérieur gauche)
    x_souris, y_souris = pyautogui.position()
    print(f"\nPosition de la souris détectée : X={x_souris}, Y={y_souris}")
    
    # 2. Calculer la zone à capturer (X_début, Y_début, X_fin, Y_fin)
    boite_capture = (x_souris, y_souris, x_souris + largeur, y_souris + hauteur)
    
    # 3. Prendre la capture d'écran
    capture = ImageGrab.grab(bbox=boite_capture, include_layered_windows=False)
    
    # 4. Définir le nom du fichier et le sauvegarder dans le dossier courant
    nom_fichier = f"capture_{int(time.time())}.png"
    chemin_sauvegarde = os.path.join(os.getcwd(), nom_fichier)
    
    capture.save(chemin_sauvegarde)
    print(f"Succès ! Capture sauvegardée sous : {chemin_sauvegarde}")

if __name__ == "__main__":
    capture_depuis_souris()
