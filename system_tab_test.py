from pywinauto.application import Application
import time
import re
from time import sleep
import psutil
import sys
import os                     # Pour la création des dossiers
from datetime import datetime # Pour l'horodatage des fichiers
from PIL import ImageGrab     # Import direct de Pillow pour un screenshot fixe et fiable
from config_loader import charger_config

# ========================================================
# CONFIGURATION DES COORDONNÉES SCREENSHOT
# ========================================================
config = charger_config()
config_capture = config["capture"]
config_application = config["application"]

OFFSET_X = config_capture["offset_x"]
OFFSET_Y = config_capture["offset_y"]
LARGEUR_BOX = config_capture["largeur_box"]
HAUTEUR_BOX = config_capture["hauteur_box"]


def calculer_boite_capture_dynamique(pane_droite):
    rect_pane = pane_droite.rectangle()
    x_depart = rect_pane.left + OFFSET_X
    y_depart = rect_pane.top + OFFSET_Y
    x_arrivee = x_depart + LARGEUR_BOX
    y_arrivee = y_depart + HAUTEUR_BOX
    return (x_depart, y_depart, x_arrivee, y_arrivee)

# ==========================================
# 1. RECUPÉRATION AUTOMATIQUE DU PID
# ==========================================
def trouver_pid_application():
    # Option A : Rechercher par le nom de l'exécutable
    nom_processus = config_application["process_name"]
    
    # Option B (Plus robuste) : Rechercher un mot-clé dans le titre de la fenêtre
    mot_cle_fenetre = config_application["window_title_keyword"]

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

pattern = re.compile(r"^[A-Za-zÀ-ÿ].*")


try:
    # On cherche dans TOUTE la fenêtre (window) un TabItem
    # dont le nom contient "Syst" suivi de n'importe quoi, puis "me" (gère le è cassé)
    onglet_systeme = window.child_window(
        control_type="TabItem", 
        title_re="Syst.*me"
    )

    # On applique en priorité ton cheat Win32 s'il a un handle
    if hasattr(onglet_systeme, 'handle') and onglet_systeme.handle:
        hwnd_tab = onglet_systeme.handle
        Application(backend="win32").connect(handle=hwnd_tab).window(handle=hwnd_tab).click()
        print("[+] Succès : Onglet 'Système' activé (Cheat Win32)")
    else:
        # Si le handle est None, click_input() utilise les coordonnées réelles de l'élément,
        # peu importe où il a bougé à l'écran suite au redémarrage.
        onglet_systeme.click_input()
        print("[+] Succès : Onglet 'Système' activé (Clic simulé)")

except Exception as e:
    print(f"[-] Erreur critique d'accès à l'onglet : {e}")
    
#liste_peripheriques = window.child_window(control_type="Pane", found_index=0) 
liste_peripheriques = window.child_window(control_type="Pane", title_re="Système")

elements_texte = liste_peripheriques.descendants(control_type="Text")

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

time.sleep(2)

# ==========================================
# 3. BOUCLE D'ACTION : DOUBLE BACKEND (ISSUE GITHUB #860 QUE TU M'AS ENVOYE)
# ==========================================
for i, (nom, element) in enumerate(zip(noms_trouves, peripheriques_a_cliquer), 1):
    print(f"[{i}/{nbr_periph}] Sélection de : {nom}...")
    boite_capture_dynamique = None
    
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
    # Quand l'élément a été séléctionné
    # on peut accéder aux tabitems dans son pane associé, qui n'existe que quand l'élément est séléctionné.
# --- BLOC DE DÉTECTION SÉCURISÉ CONTRE LES FAUX POSITIFS ---
    try:
        print(f"   [...] Attente du chargement du panneau pour '{nom}'...")
        pane_droite = window.child_window(control_type="Pane", found_index=0)
        pane_droite.wait('ready', timeout=5)
        boite_capture_dynamique = calculer_boite_capture_dynamique(pane_droite)
        
        textes_trouves = pane_droite.descendants(control_type="TabItem")
        
        tabs_a_cliquer = []
        noms_tabs_trouves = []
        
        liste_noire = [
            "périphériques", 
            "système",
            "transmetteurs",
            "niveaux sonores",
            nom.lower().strip(), 
            "profils télécommandes", 
            "profils de télécommande"
        ]
        
        for el in textes_trouves:
            texte = el.window_text()
            if not texte and el.texts():
                texte = el.texts()[0]
                
            texte_nettoye = texte.strip()
            
            if pattern.match(texte_nettoye) and (texte_nettoye.lower() not in liste_noire):
                noms_tabs_trouves.append(texte_nettoye)
                tabs_a_cliquer.append(el)

        nbr_tabs = len(noms_tabs_trouves)
        print(f"   [+] Nombre de tabs trouvés : {nbr_tabs}")
        print("   [+] Tabs détectés :", noms_tabs_trouves)
        
    except Exception as e:
        print(f"   [!] Pas d'onglets de type 'TabItem' détectés pour '{nom}'")
        nbr_tabs = 0
        noms_tabs_trouves = []
        tabs_a_cliquer = []

    # Préparation du dossier et de la date commune
    nom_dossier_propre = "".join(c for c in nom if c.isalnum() or c in (' ', '_', '-')).strip()
    if not os.path.exists(nom_dossier_propre):
        os.makedirs(nom_dossier_propre)
        print(f"   [+] Dossier créé : {nom_dossier_propre}/")
    
    date_str = datetime.now().strftime("%d-%m-%Y_%Hh%M")

    # ==========================================
    # LOOP EN ACTION : CLICS ET CAPTURES PAR ONGLET
    # ==========================================
    if nbr_tabs > 0:
        print(f"   [→] Début du parcours des {nbr_tabs} sous-onglets...")
        
        for j, (nom_tab, tab_el) in enumerate(zip(noms_tabs_trouves, tabs_a_cliquer), 1):
            print(f"       [{j}/{nbr_tabs}] Clic physique sur l'onglet : {nom_tab}")
            
            try:
                window.set_focus()
                tab_el.click_input()
                time.sleep(1.5)  # Pause pour charger le contenu de l'onglet
                
                # --- CAPTURE DE L'ONGLET EN COURS ---
                nom_tab_propre = "".join(c for c in nom_tab if c.isalnum() or c in (' ', '_', '-')).strip()
                nom_fichier = f"capture_{nom_tab_propre}_{date_str}.png"
                chemin_complet = os.path.join(nom_dossier_propre, nom_fichier)
                
                img = ImageGrab.grab(bbox=boite_capture_dynamique, include_layered_windows=False)
                img.save(chemin_complet)
                print(f"       [+] Screenshot dynamique enregistré : {chemin_complet}")
                
            except Exception as e:
                print(f"       [-] Échec sur l'onglet {nom_tab} : {e}")
    else:
        # --- CAS DE SECOURS : PAS D'ONGLETS DETECTES ---
        print("   [=] Aucun sous-onglet. Capture de la page principale...")
        try:
            nom_fichier = f"capture_principal_{date_str}.png"
            chemin_complet = os.path.join(nom_dossier_propre, nom_fichier)
            
            if boite_capture_dynamique is None:
                raise RuntimeError("Boite de capture dynamique indisponible.")

            img = ImageGrab.grab(bbox=boite_capture_dynamique, include_layered_windows=False)
            img.save(chemin_complet)
            print(f"   [+] Screenshot principal dynamique enregistré : {chemin_complet}")
        except Exception as e:
            print(f"   [-] Impossible de générer la capture pour {nom} : {e}")

    print("-" * 50)
    time.sleep(1)

print("Parcours terminé avec succès !")
