import numpy as np            # Importation de la bibliothèque NumPy pour les opérations mathématiques avancées
import cv2                    # Importation de la bibliothèque OpenCV pour le traitement d'images et de vidéos
import mediapipe as mp        # Importation de MediaPipe pour la détection et le suivi des poses humaines

# VARIABLES GLOBALES ----------------------------------------------------------------------------------------------------------

# Initialisation des modules MediaPipe pour la détection des poses et le dessin des landmarks
mp_holistic = mp.solutions.holistic          # Module Holistic pour la détection de la posture complète
mp_drawing = mp.solutions.drawing_utils      # Utilitaires pour le dessin des points clés (landmarks) détectés

# SEUILS DE CLASSIFICATION ERGONOMIQUE ----------------------------------------------------------------------------------------

# Dictionnaire contenant les seuils pour la classification ergonomique des angles articulaires
# Chaque articulation a des seuils pour les zones verte, orange et rouge en fonction des degrés de l'angle
thresholds = {
    'extension_coudes': {
        'green': (75, 140),                     # Zone verte : angle entre 75° et 140°
        'orange': [(0, 75), (140, float('inf'))],  # Zone orange : angles inférieurs à 75° ou supérieurs à 140°
        'red': (0, 0)                           # Zone rouge : non définie ici (placeholder)
    },
    'rotation_epaules': {
        'green': (0, 80),
        'orange': [(80, 90)],
        'red': (90, float('inf'))
    },
    'elevation_epaules': {
        'green': (0, 90),
        'orange': [(90, 120)],
        'red': (120, float('inf'))
    },
    'flexion_cou': {
        'green': (-5, 20),
        'orange': [(20, 40)],
        'red': (40, float('inf'))
    },
    'rotation_buste': {
        'green': (0, 0),
        'orange': [(0, 40)],
        'red': (40, float('inf'))
    },
    'flexion_buste': {
        'green': (0, 20),
        'orange': [(20, 45)],
        'red': (45, float('inf'))
    },
}

# Seuils pour la répétitivité des mobilisations articulaires
repetitivite_thresholds = {
    'reduit': (0, 5),              # Moins de 5% du temps de travail
    'limite': (5, 20),             # Entre 5% et 20% du temps de travail
    'a_eviter': (20, float('inf')) # Plus de 20% du temps de travail
}

# Seuils pour le maintien des postures à risques
maintien_posture_thresholds = {
    'reduit': (0, 3),              # Moins de 3% du temps de travail
    'limite': (3, 10),             # Entre 3% et 10% du temps de travail
    'a_eviter': (10, float('inf')) # Plus de 10% du temps de travail
}

# Seuils pour la récupération musculaire
recuperation_musculaire_thresholds = {
    'verte': (5, float('inf')),    # Plus de 5% du temps
    'orange': (1, 5),              # Entre 1% et 5%
    'rouge': (0, 1)                # Moins de 1%
}

# Seuils pour l'effort de préhension
effort_prehension_thresholds = {
    'verte': (50, float('inf')),   # Plus de 50% du temps (effort faible)
    'orange': (25, 50),            # Entre 25% et 50% du temps (effort modéré)
    'rouge': (0, 25)               # Moins de 25% du temps (effort élevé)
}

# FONCTIONS UTILITAIRES -------------------------------------------------------------------------------------------------------

def calculate_image_quality(image):
    """
    Calculer la qualité de l'image en fonction de la luminosité et de la netteté.
    Utilisé pour ajuster la complexité du modèle MediaPipe.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Conversion en niveaux de gris
    brightness = np.mean(gray) / 255.0              # Calcul de la luminosité moyenne normalisée (entre 0 et 1)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var() / 100.0  # Calcul de la netteté (variance du Laplacien)
    # Combinaison de la luminosité et de la netteté pour obtenir un score de qualité entre 0 et 1
    quality = min(1.0, max(0.0, 0.5 * brightness + 0.5 * (sharpness / (sharpness + 1))))
    return quality

def calculate_angle(a, b, c):
    """
    Calculer l'angle en degrés formé par trois points a, b, c.
    L'angle est au point b entre les segments ba et bc.
    """
    ba = np.array(a) - np.array(b)  # Vecteur ba (de b à a)
    bc = np.array(c) - np.array(b)  # Vecteur bc (de b à c)
    # Calcul du produit scalaire et des normes des vecteurs
    dot_product = np.dot(ba, bc)
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    # Vérification pour éviter une division par zéro
    if norm_ba == 0 or norm_bc == 0:
        return 0
    # Calcul du cosinus de l'angle
    cos_angle = dot_product / (norm_ba * norm_bc)
    # Limitation du cosinus pour éviter les erreurs numériques
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    # Conversion en angle en degrés
    angle = int(np.degrees(np.arccos(cos_angle)))
    return angle

def preprocess_image(image):
    """
    Prétraiter l'image pour améliorer la détection des points clés.
    Applique une égalisation d'histogramme et un flou gaussien.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)        # Conversion en niveaux de gris
    equalized = cv2.equalizeHist(gray)                    # Égalisation de l'histogramme pour améliorer le contraste
    blurred = cv2.GaussianBlur(equalized, (5, 5), 0)      # Application d'un flou gaussien pour réduire le bruit
    processed_image = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)  # Conversion en BGR pour compatibilité avec MediaPipe
    return processed_image

def classify_angle(angle, thresholds):
    """
    Classer un angle donné dans une zone de risque (1: vert, 2: orange, 3: rouge) selon les seuils fournis.
    """
    if thresholds['green'][0] <= angle <= thresholds['green'][1]:
        return 1  # Zone verte : angle dans la plage acceptable
    elif any(lower <= angle <= upper for (lower, upper) in thresholds['orange']):
        return 2  # Zone orange : angle dans la plage à surveiller
    elif angle >= thresholds['red'][0]:
        return 3  # Zone rouge : angle dans la plage à éviter
    else:
        return 0  # Non classé : angle hors des plages définies

def extract_keypoints(landmarks):
    """
    Extraire les points clés nécessaires des landmarks détectés par MediaPipe.
    Renvoie un dictionnaire avec les coordonnées normalisées (entre 0 et 1).
    """
    def get_landmark_value(landmark):
        if landmark:
            return [landmark.x, landmark.y]
        else:
            return None

    # Extraction des coordonnées des points clés
    keypoints = {
        'shoulder_left': get_landmark_value(landmarks[mp_holistic.PoseLandmark.LEFT_SHOULDER.value]),
        'elbow_left': get_landmark_value(landmarks[mp_holistic.PoseLandmark.LEFT_ELBOW.value]),
        'wrist_left': get_landmark_value(landmarks[mp_holistic.PoseLandmark.LEFT_WRIST.value]),
        'shoulder_right': get_landmark_value(landmarks[mp_holistic.PoseLandmark.RIGHT_SHOULDER.value]),
        'elbow_right': get_landmark_value(landmarks[mp_holistic.PoseLandmark.RIGHT_ELBOW.value]),
        'wrist_right': get_landmark_value(landmarks[mp_holistic.PoseLandmark.RIGHT_WRIST.value]),
    }

    # Calcul du point du cou (milieu des épaules)
    left_shoulder = keypoints['shoulder_left']
    right_shoulder = keypoints['shoulder_right']

    if left_shoulder and right_shoulder:
        neck = [
            (left_shoulder[0] + right_shoulder[0]) / 2,
            (left_shoulder[1] + right_shoulder[1]) / 2
        ]
        keypoints['neck'] = neck
    else:
        keypoints['neck'] = None

    return keypoints

def display_results(image, presence_personne, ergonomic_indicator, risk_zone, result):
    """
    Afficher les résultats de l'analyse sur l'image en superposant du texte.
    """
    # Affichage de la présence d'une personne détectée
    cv2.putText(image, f'Présence personne: {presence_personne}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    # Affichage de l'indicateur ergonomique et de la zone de risque
    cv2.putText(image, f'Indicateur Ergonomique: {ergonomic_indicator} (Zone {risk_zone})', (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    # Affichage du résultat détaillé
    cv2.putText(image, f'Résultat: {result}', (10, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

def detect_actions_techniques_in_image(image):
    """
    Détecter des "actions techniques" dans l'image.
    Cette fonction est simplifiée et sert de placeholder pour une implémentation plus avancée.
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Conversion en niveaux de gris si nécessaire

    image_normalized = image / 255.0  # Normalisation des valeurs de pixel entre 0 et 1

    actions_mask = np.zeros_like(image_normalized)  # Création d'un masque vide pour les actions techniques

    # Détection des pixels locaux maximaux (pic) en comparant avec les voisins
    actions_mask[1:-1, 1:-1] = (
        (image_normalized[1:-1, 1:-1] > image_normalized[:-2, 1:-1]) &  # Supérieur au pixel au-dessus
        (image_normalized[1:-1, 1:-1] > image_normalized[2:, 1:-1]) &    # Supérieur au pixel en dessous
        (image_normalized[1:-1, 1:-1] > image_normalized[1:-1, :-2]) &   # Supérieur au pixel à gauche
        (image_normalized[1:-1, 1:-1] > image_normalized[1:-1, 2:])      # Supérieur au pixel à droite
    )

    actions = np.argwhere(actions_mask)  # Extraction des coordonnées des actions techniques détectées
    actions = [(i, j) for i, j in actions]  # Conversion en liste de tuples (ligne, colonne)

    return actions

def estimateur(image):
    """
    Fonction principale pour analyser la posture dans une image donnée.
    """
    image_original = image.copy()  # Copie de l'image originale pour la détection des actions techniques
    image = preprocess_image(image)  # Prétraitement de l'image pour améliorer la détection

    # Calcul de la qualité de l'image pour ajuster la complexité du modèle
    image_quality = calculate_image_quality(image)
    model_complexity = 1 if image_quality < 0.5 else 2  # Modèle plus simple pour les images de moindre qualité

    result = "_0_0_0_0_0_0_0_0_0_"  # Initialisation du résultat par défaut

    # Initialisation du modèle MediaPipe Holistic avec les paramètres appropriés
    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=model_complexity
    ) as holistic:
        try:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Conversion en RGB pour MediaPipe
            results = holistic.process(image_rgb)  # Traitement de l'image pour la détection des poses

            presence_personne = 1 if results.pose_landmarks else 0  # Vérification de la présence d'une personne

            if not presence_personne:
                print("Aucune personne détectée.")
                return result  # Retourner le résultat par défaut si aucune personne n'est détectée

            landmarks = results.pose_landmarks.landmark  # Extraction des landmarks détectés

            # Dessiner les landmarks sur l'image pour visualisation
            mp_drawing.draw_landmarks(
                image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

            keypoints = extract_keypoints(landmarks)  # Extraction des points clés nécessaires

            # Vérification de la validité des points clés extraits
            for key, value in keypoints.items():
                if value is None or not isinstance(value, list) or len(value) != 2:
                    print(f"Erreur: Point clé '{key}' invalide ou manquant.")
                    return result  # Retourner le résultat par défaut en cas d'erreur

            required_keys = ['neck', 'shoulder_left', 'shoulder_right']
            if not all(keypoints[key] is not None for key in required_keys):
                print("Erreur: Points clés manquants. Impossible de continuer l'analyse.")
                return result

            # Calcul de l'angle de flexion du cou
            flexion_cou = calculate_angle(
                keypoints['shoulder_left'], keypoints['neck'], keypoints['shoulder_right'])

            # Classification de l'angle de flexion du cou selon les seuils
            flexion_cou_score = classify_angle(flexion_cou, thresholds['flexion_cou'])

            # Calcul de l'indicateur ergonomique basé sur le score de flexion du cou
            ergonomic_indicator = flexion_cou_score

            # Détermination de la zone de risque globale
            risk_zone = 1 if ergonomic_indicator == 1 else 2 if ergonomic_indicator == 2 else 3

            # Détection des actions techniques dans l'image originale
            detected_actions = detect_actions_techniques_in_image(image_original)
            num_actions = len(detected_actions)  # Nombre d'actions techniques détectées

            # Initialisation des scores pour les autres facteurs ergonomiques (placeholder)
            repetitivite_score = 1         # Score de répétitivité des mouvements
            maintien_posture_score = 1     # Score de maintien des postures à risque
            recuperation_score = 1         # Score de récupération musculaire
            prehension_score = 1           # Score de l'effort de préhension

            # Construction de la chaîne de résultats avec les valeurs calculées
            result = f'_{flexion_cou}_{flexion_cou_score}_{presence_personne}_{risk_zone}_{num_actions}_{repetitivite_score}_{maintien_posture_score}_{recuperation_score}_{prehension_score}'

            # Affichage des résultats sur l'image
            display_results(image, presence_personne, ergonomic_indicator, risk_zone, result)

            # Affichage des actions techniques détectées en dessinant des cercles rouges
            for (i, j) in detected_actions:
                cv2.circle(image, (j, i), 5, (0, 0, 255), -1)

            print(result)  # Affichage du résultat dans la console pour suivi

        except (TypeError, ValueError) as e:
            # Gestion des erreurs lors du calcul de l'angle ou de l'extraction des points clés
            print(f"Erreur lors du calcul de l'angle: {e}. Cela peut être dû à des points clés manquants ou incorrects.")
            return result
        except Exception as e:
            # Gestion des autres exceptions éventuelles
            print(f"Erreur lors du traitement de l'image: {e}")
            return result

    return result  # Retourner le résultat de l'analyse

# GESTION DU FLUX VIDÉO ------------------------------------------------------------------------------------------------------

def main():
    """
    Fonction principale pour gérer le flux vidéo et appliquer l'analyse de posture à chaque image.
    """
    cap = cv2.VideoCapture(0)  # Ouverture de la webcam (remplacer par 'video.mp4' pour un fichier vidéo)
    if not cap.isOpened():
        print("Erreur: Impossible d'accéder à la vidéo.")  # Message d'erreur si la vidéo n'est pas accessible
        return

    while True:
        ret, frame = cap.read()  # Lecture d'une image du flux vidéo
        if not ret:
            print("Fin de la vidéo ou erreur de lecture.")  # Fin de la vidéo ou erreur lors de la lecture
            break

        result = estimateur(frame)  # Appel de la fonction estimateur pour analyser la posture dans l'image

        cv2.imshow('Estimation Posture', frame)  # Affichage de l'image avec les annotations

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break  # Quitter la boucle si la touche 'q' est pressée

    cap.release()  # Libération des ressources associées au flux vidéo
    cv2.destroyAllWindows()  # Fermeture de toutes les fenêtres OpenCV

# POINT D'ENTRÉE DU SCRIPT ---------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()  # Appel de la fonction principale pour démarrer le programme