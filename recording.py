#!/usr/bin/python

# Bibliothèques **************************************************
import subprocess             # Pour exécuter des commandes système
import time                   # Pour gérer les délais et les temporisations
from datetime import datetime # Pour gérer les dates et heures
from openni import openni2    # Pour interfacer avec les caméras OpenNI
from openni import _openni2 as c_api  # API interne pour des fonctionnalités avancées
import paramiko               # Pour établir des connexions SSH
import socket                 # Pour gérer les communications réseau bas niveau
import sys                    # Pour accéder à certaines variables système
import os                     # Pour interagir avec le système d'exploitation (suppression de fichiers)
import numpy as np            # Pour les opérations sur les tableaux numériques
import cv2                    # Pour le traitement d'images et de vidéos
import logging                # Pour la gestion avancée des messages de log
from termcolor import colored # Pour afficher du texte coloré dans le terminal (facultatif avec logging)
from estimateur_posture import *  # Importation des fonctions d'analyse de posture

# Configuration du logging ***************************************
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constantes *****************************************************
IP_CONCENTRATEUR = 70  # Les deux derniers chiffres de l'adresse IP du concentrateur
REPERTOIRE_SAUVEGARDE = "/home/Share/Enregistrements/"  # Répertoire pour sauvegarder les images
PING_TIMEOUT = 100  # Temps d'attente pour le ping (en millisecondes)

# Fonctions cycliques ********************************************

def fct_periodique_1s():
    """
    Fonction principale qui s'exécute périodiquement.
    Elle capture une image, l'analyse, et envoie les résultats au concentrateur.
    """
    global num_poste, app_is_on, recordingstr, pres_cam, mdv, result_analyse
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Création d'un socket TCP
    try:
        # Connexion au concentrateur
        client_socket.connect((fullIP_Concentrateur, 50000))
        logging.info("Connecté au concentrateur.")

        while True:
            demande_recording = "yes"  # Demande d'enregistrement (fixée à "yes" par défaut)
            if demande_recording == "yes":
                recordingstr = "yes"
                filename = record()  # Capture d'une image
                if filename != "":
                    # Analyse de l'image capturée
                    result_analyse = estimateur([filename])
                    # Suppression de l'image après analyse pour économiser l'espace disque
                    try:
                        os.remove(filename)
                        logging.debug(f"Fichier {filename} supprimé.")
                    except Exception as e:
                        logging.error(f"Erreur lors de la suppression du fichier {filename}: {e}")
                    mdv_app()  # Mise à jour du compteur mdv
                    now_message = datetime.now()
                    date_message = now_message.strftime("%d_%m_%Y_%H_%M_%S")
                    app_is_on = "yes"
                    # Préparation du message à envoyer au concentrateur
                    message_emission = f"{num_poste}_{app_is_on}_{recordingstr}_{pres_cam}_{mdv}_0{result_analyse}"
                    logging.info(f"Message prêt à être envoyé: {message_emission}")
                    client_socket.send(message_emission.encode())  # Envoi du message
            else:
                recordingstr = "no"

    except Exception as e:
        # Gestion des exceptions éventuelles
        logging.error(f"fct_periodique_1s() - Exception: {e}")
    finally:
        client_socket.close()  # Fermeture du socket
        logging.info("Socket fermé.")

def record():
    """
    Capture une image depuis la caméra et l'enregistre dans un fichier.
    Retourne le nom du fichier créé.
    """
    global dev, color_stream
    try:
        # Démarrage du flux de la caméra
        color_stream.start()
        color_stream.set_video_mode(c_api.OniVideoMode(
            pixelFormat=c_api.OniPixelFormat.ONI_PIXEL_FORMAT_RGB888,
            resolutionX=640, resolutionY=480, fps=30))
        # Lecture d'une frame depuis le flux
        color_frame = color_stream.read_frame()
        color_frame_data = color_frame.get_buffer_as_uint8()
        # Conversion des données en image
        color_img = np.frombuffer(color_frame_data, dtype=np.uint8)
        color_img.shape = (480, 640, 3)
        color_img = color_img[..., ::-1]  # Conversion BGR vers RGB
        # Génération du nom de fichier avec la date et l'heure actuelles
        now = datetime.now()
        date = now.strftime("%d_%m_%Y_%H_%M_%S_%f")
        filename = f"{REPERTOIRE_SAUVEGARDE}img_{date}.jpg"
        # Sauvegarde de l'image
        cv2.imwrite(filename, color_img)
        logging.debug(f"Image enregistrée sous {filename}")
        # Enregistrement du dernier fichier capturé
        with open("Last_img.txt", "w") as fichier:
            fichier.write(filename)
        return filename
    except Exception as e:
        # Gestion des exceptions éventuelles
        logging.error(f"record() - Exception occurred: {e}")
        return ""

def Sortie_programme():
    """
    Quitte proprement le programme.
    """
    logging.info("Arrêt du programme.")
    sys.exit(0)

def cmd_terminal_local(command):
    """
    Exécute une commande shell locale.
    """
    try:
        subprocess.call(command, shell=True)
    except Exception as e:
        # Gestion des exceptions éventuelles
        logging.error(f"cmd_terminal_local() - Exception: command = {command}, error: {e}")

def ping(host):
    """
    Vérifie si une machine est accessible via un ping.
    Retourne True si le ping réussit, False sinon.
    """
    try:
        result = subprocess.run(['ping', '-c', '1', '-w', str(PING_TIMEOUT), host], capture_output=True)
        return result.returncode == 0
    except Exception as e:
        # Gestion des exceptions éventuelles
        logging.error(f"ping() - Exception: {e}")
        return False

def initanyusb():
    """
    Initialise la caméra en redémarrant le port USB distant via SSH.
    """
    global ip_anyusb, portusb
    try:
        # Détermination de l'IP du hub USB distant en fonction du numéro de poste
        ip_anyusb = 60 if (1 <= int(num_poste) < 9) else 61
        hostname = f'10.10.10.{ip_anyusb}'
        username = 'admin'
        password = 'Masternaute2023*'  # Mot de passe pour la connexion SSH

        # Connexion SSH au hub USB distant
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=username, password=password)

        # Détermination du port USB à redémarrer
        portusb = int(num_poste) if (1 <= int(num_poste) < 9) else int(num_poste) - 8
        # Commande pour redémarrer le port USB
        client.exec_command(f'system anywhereusb powercycle port{portusb}')
        logging.info("Reboot caméra en cours...")
        client.close()
        time.sleep(10)  # Attente du redémarrage
        logging.info("Redémarrage de la caméra effectué.")
    except Exception as e:
        # Gestion des exceptions éventuelles
        logging.error(f"initanyusb() - Exception: {e}")

def check_cam():
    """
    Vérifie si la caméra est connectée en utilisant la commande 'lsusb'.
    Retourne True si la caméra est détectée, False sinon.
    """
    try:
        result = subprocess.run('lsusb | grep "Orbbec"', shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            logging.info("Caméra détectée.")
            return True
        else:
            logging.warning("Caméra non détectée. Tentative de réinitialisation...")
            initanyusb()  # Tentative de réinitialisation de la caméra
            return False
    except Exception as e:
        # Gestion des exceptions éventuelles
        logging.error(f"check_cam() - Exception: {e}")
        return False

def mdv_app():
    """
    Incrémente le compteur mdv modulo 60.
    """
    global mdv
    try:
        mdv = (mdv + 1) % 60
    except Exception as e:
        # Gestion des exceptions éventuelles
        logging.error(f"mdv_app() - Exception: {e}")

# =======================================================================================================================
#                                             *** PROGRAMME PRINCIPAL ***
# =======================================================================================================================

if __name__ == "__main__":
    logging.info("*************** NE PAS FERMER ***************")
    logging.info("********** INITIALISATION **********")

    # Variables et paramètres
    plageIP = "10.10.10."  # Plage d'adresses IP
    fullIP_Concentrateur = f"{plageIP}{IP_CONCENTRATEUR}"  # Adresse IP complète du concentrateur

    color_img = None
    tps_traitement = 0.4  # Temps de traitement estimé
    delai_pause = 4.0 - tps_traitement  # Délai de pause entre les traitements
    mdv = 0  # Compteur mdv
    nom_poste = socket.gethostname()  # Nom de la machine
    num_poste = nom_poste.replace("pc-camera", "")  # Extraction du numéro de poste
    app_is_on = "no"
    recording = "no"
    pres_cam = "no"
    result_analyse = "_0_1_2_3_4_5_6_7_8_9"  # Valeur par défaut des résultats d'analyse

    logging.info("Paramètres définis.")

    # Vérification de la présence du concentrateur
    logging.info(f"Vérification de la présence du Concentrateur @{fullIP_Concentrateur}...")
    success = ping(host=fullIP_Concentrateur)

    if success:
        logging.info("Concentrateur accessible.")
    else:
        logging.warning("Concentrateur inaccessible.")

    # Initialisation de la caméra
    initanyusb()

    # Vérification de la connexion de la caméra
    if not check_cam():
        pres_cam = "no"
        while not check_cam():
            time.sleep(2)

    # Initialisation du module OpenNI2 pour la caméra
    openni2.initialize()
    logging.info("Module OpenNI2 initialisé.")
    dev = openni2.Device.open_any()
    logging.info("Caméra détectée et connectée.")
    color_stream = dev.create_color_stream()
    pres_cam = "yes"

    logging.info("********** APPLICATION OPÉRATIONNELLE **********")
    logging.info("Échanges en cours avec le concentrateur.")

    # Démarrage de la fonction principale
    fct_periodique_1s()

    logging.info("FIN DE PROGRAMME")
    Sortie_programme()

# =======================================================================================================================
#                                           *** FIN PROGRAMME PRINCIPAL ***
# =======================================================================================================================