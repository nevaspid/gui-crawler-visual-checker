import pyautogui
import time

print("Déplace ta souris sur la zone. Appuie sur CTRL+C pour arrêter.")
try:
    while True:
        # Récupère les coordonnées X, Y de la souris
        x, y = pyautogui.position()
        # Le \r permet d'effacer et de réécrire sur la même ligne
        print(f"Position actuelle de la souris -> X: {x}, Y: {y}      ", end="\r")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nTerminé.")
    
#X233 Y105
#X1363 Y700