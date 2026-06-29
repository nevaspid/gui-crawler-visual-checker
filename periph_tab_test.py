from pywinauto.application import Application
import time
import re
from time import sleep
import psutil
import sys
import os                     # Pour la création des dossiers
from datetime import datetime # Pour l'horodatage des fichiers
from PIL import ImageGrab     # Import direct de Pillow pour un screenshot fixe et fiable

# ========================================================
# CONFIGURATION DES COORDONNÉES SCREENSHOT (MÀJ)
# ========================================================
X_DEPART = 233   
Y_DEPART = 105   
X_ARRIVEE = 1363  
Y_ARRIVEE = 700  

OFFSET_X = 0
OFFSET_Y = 0
LARGEUR_BOX = 1130
HAUTEUR_BOX = 595

boite_capture = (X_DEPART, Y_DEPART, X_ARRIVEE, Y_ARRIVEE)

# ==========================================
# 1. RECUPÉRATION AUTOMATIQUE DU PID
# ==========================================
def trouver_pid_application():
    # Option A : Rechercher par le nom de l'exécutable
    nom_processus = "javaw.exe" 
    
    # Option B (Plus robuste) : Rechercher un mot-clé dans le titre de la fenêtre
    mot_cle_fenetre = "Green" 

    print(f"Recherche automatique du processus...")
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # On cible le processus Java
            if proc.info['name'] and nom_processus in proc.info['name'].lower():
                # On vérifie si ce processus possède une fenêtre avec notre mot-clé
                # (Évite de se connecter à un autre processus Java en arrière-plan)
                app_temp = Application(backend="uia").connect(process=proc.info['pid'])
                if mot_cle_fenetre.lower() in app_temp.top_window().window_text().lower():
                    return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, Exception):
            continue
            
    return None

# Récupération dynamique
pid = trouver_pid_application()

if pid is None:
    print("[-] Impossible de trouver le PID de l'application.")
    print("Vérifie que l'application est bien lancée et que le nom/mot-clé correspond.")
    sys.exit(1)

print(f"[+] Application trouvée ! PID détecté automatiquement : {pid}")

# Connexion à l'application avec le PID trouvé
app = Application(backend="uia").connect(process=pid)
window = app.top_window()

# ==========================================
# 2. EXTRACTION DES PÉRIPHÉRIQUES (TON CODE)
# ==========================================
liste_peripheriques = window.child_window(control_type="Pane", found_index=0) 
elements_texte = liste_peripheriques.descendants(control_type="Text")

pattern = re.compile(r"^\d+-")

peripheriques_a_cliquer = []
noms_trouves = []

for el in elements_texte:
    texte = el.window_text()
    if pattern.match(texte):
        noms_trouves.append(texte)
        peripheriques_a_cliquer.append(el)

nbr_periph = len(noms_trouves)
print(f"Nombre de périphériques trouvés : {nbr_periph}")
print("Périphériques détectés :", noms_trouves)
print("-" * 50)

# ==========================================
# 3. BOUCLE D'ACTION : DOUBLE BACKEND (TON CODE + ISSUE GITHUB #860 QUE TU AS TROUVE)
# ==========================================
for i, (nom, element) in enumerate(zip(noms_trouves, peripheriques_a_cliquer), 1):
    print(f"[{i}/{nbr_periph}] Sélection de : {nom}...")
    
    # Définition des différents niveaux de parents
    parent1 = element.parent() if hasattr(element, 'parent') else None
    parent2 = parent1.parent() if parent1 and hasattr(parent1, 'parent') else None
    parent3 = parent2.parent() if parent2 and hasattr(parent2, 'parent') else None

    # ASTUCE ISSUE #860 : On récupère le Handle Windows (HWND) du conteneur SWT
    # Cela permet d'envoyer un vrai message de clic Win32 au composant
    try:
        hwnd = element.handle
        # On crée une passerelle Win32 éphémère juste pour le clic
        app_win32 = Application(backend="win32").connect(handle=hwnd)
        el_win32 = app_win32.window(handle=hwnd)
    except Exception:
        el_win32 = element # Secours si la conversion directe échoue

    #Tests d'accès au Pane selon ton exemple de code :
    # --- NIVEAU 0 : L'ÉLÉMENT TEXTE ---
    #try:
    #    element.select()
    #    print("Succès : element.select()")
    #except Exception:
    #    try:
    #        # On tente le clic via la passerelle Win32 issue du ticket #860
    #        el_win32.click()
    #        print("Succès : element.click() (via Win32 Bridge)")
    #    except Exception:
    #        try:
    #            if hasattr(element, 'toggle'): element.toggle()
    #            print("Succès : element.toggle()")
    #        except Exception:
    #            pass

    # --- NIVEAU 1 : LE PARENT 1 ---
    if parent1:
        try:
            parent1.select()
            print("Succès : parent1.select()")
        except Exception:
            try:
                # Tentative de clic Win32 sur le parent
                if hasattr(parent1, 'handle'):
                    Application(backend="win32").connect(handle=parent1.handle).window(handle=parent1.handle).click()
                else:
                    parent1.click()
                print("Succès : parent1.click()")
            except Exception:
                try:
                    if hasattr(parent1, 'toggle'): parent1.toggle()
                    print("Succès : parent1.toggle()")
                except Exception:
                    pass

    # --- NIVEAU 2 : LE PARENT 2 ---
    #if parent2:
    #    try:
    #        parent2.select()
    #        print("Succès : parent2.select()")
    #    except Exception:
    #        try:
    #            if hasattr(parent2, 'handle'):
    #                Application(backend="win32").connect(handle=parent2.handle).window(handle=parent2.handle).click()
    #            else:
    #                parent2.click()
    #            print("Succès : parent2.click()")
    #        except Exception:
    #            try:
    #                if hasattr(parent2, 'toggle'): parent2.toggle()
    #                print("Succès : parent2.toggle()")
    #            except Exception:
    #                pass

    # --- NIVEAU 3 : LE PARENT 3 ---
    #if parent3:
    #    try:
    #        parent3.select()
    #        print("Succès : parent3.select()")
    #    except Exception:
    #        try:
    #            if hasattr(parent3, 'handle'):
    #                Application(backend="win32").connect(handle=parent3.handle).window(handle=parent3.handle).click()
    #            else:
    #                parent3.click()
    #            print("Succès : parent3.click()")
    #        except Exception:
    #            try:
    #                if hasattr(parent3, 'toggle'): parent3.toggle()
    #                print("Succès : parent3.toggle()")
    #            except Exception:
    #                pass

    # Pause de deux secondes demandée
    time.sleep(2)

    # --- PRISE DU SCREENSHOT ET STOCKAGE DOSSIER ---
    try:
        # Nettoyage du nom pour créer un dossier Windows valide
        nom_dossier_propre = "".join(c for c in nom if c.isalnum() or c in (' ', '_', '-')).strip()
        
        # On s'assure que le dossier du périphérique existe
        if not os.path.exists(nom_dossier_propre):
            os.makedirs(nom_dossier_propre)
            print(f"   [+] Dossier créé : {nom_dossier_propre}/")
            
        # Formatage de la date du jour
        date_str = datetime.now().strftime("%d-%m-%Y_%Hh%M")
        nom_fichier = f"capture_{date_str}.png"
        chemin_complet = os.path.join(nom_dossier_propre, nom_fichier)
        
        # UTILISATION DE PILLOW DIRECT : capture la bbox de l'écran sans passer par l'API Pywinauto
        img = ImageGrab.grab(bbox=boite_capture)
        img.save(chemin_complet)
        print(f"   [+] Screenshot enregistré : {chemin_complet}")
    except Exception as e:
        print(f"   [-] Impossible de générer la capture pour {nom} : {e}")

print("Parcours terminé avec succès !")