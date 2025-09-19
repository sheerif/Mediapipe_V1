# MediaPipe V1 - Projet de Détection et Analyse de Posture

## Version 1.0 (Last Version)

Ce projet utilise MediaPipe pour l'analyse ergonomique de posture en temps réel.

## Installation des Dépendances

```bash
pip install -r requirements.txt
```

## Scripts Principaux

- **`recording.py`**: Script principal pour la capture d'images et l'analyse en temps réel
- **`estimateur_posture.py`**: Module d'analyse de posture utilisant MediaPipe  
- **`analyse_posture.py`**: Script d'exemple pour tester l'analyse sur une image

## Corrections Version 1.0

- ✅ Correction de l'import circulaire dans `analyse_posture.py`
- ✅ Correction de l'appel de fonction `estimateur()` avec le bon type de paramètre
- ✅ Ajout de la création automatique du répertoire de sauvegarde
- ✅ Documentation des dépendances dans `requirements.txt`
- ✅ Ajout des informations de version dans tous les scripts