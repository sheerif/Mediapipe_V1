import cv2
from analyse_posture import estimateur

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