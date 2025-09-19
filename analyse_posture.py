"""
MediaPipe V1 - Analyse de Posture (Example Script)
Version: 1.0 (Last Version)
Description: Script d'exemple pour tester l'analyse de posture sur une image
"""

import cv2
from estimateur_posture import estimateur

# Charger une image depuis un fichier
image = cv2.imread('chemin/vers/votre/image.jpg')

# Vérifier que l'image a été correctement chargée
if image is not None:
    # Appeler la fonction estimateur
    resultat = estimateur(image)
    print("Résultat de l'analyse :", resultat)
    # Afficher l'image avec les annotations
    cv2.imshow('Analyse Posture', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("Erreur : Impossible de charger l'image.")