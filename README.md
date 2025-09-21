# Mediapipe_V1 — Posture & Action Analysis (MediaPipe)

> **Version :** 2025-09-21 · **Langue :** FR  
> Analyse de posture en temps réel basée sur **MediaPipe** et **OpenCV**.  
> Ce dépôt contient un noyau d’estimation/évaluation posturale — pensé pour être utilisé seul (démo) **ou** intégré dans un système plus large (ex. *Dernière‑Main* : enregistrement, GUI, exports).

---

## 1) Objectifs

- Extraire des **landmarks** (corps/mains/visage) avec **MediaPipe**.  
- Calculer des **angles articulaires**, détecter des **postures**/patterns gestuels.  
- Fournir des **indicateurs** utiles à la prévention des **TMS** et à l’alimentation du **DUER** (Document Unique).

---

## 2) Contenu du dépôt

```
Mediapipe_V1/
├─ analyse_posture.py        # Pipeline d'analyse: capture + MediaPipe + métriques/angles
├─ estimateur_posture.py     # Fonctions d'estimation: calculs, règles/seuils, scores
├─ recording.py              # Mode headless simple (enregistrement/traitement sans UI)
└─ README.md                 # Ce fichier
```
> Les noms sont indicatifs de rôle ; adaptez selon vos variantes de code.

---

## 3) Installation

### 3.1 Prérequis système (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-tk libgl1 libglib2.0-0 v4l-utils
```

### 3.2 Environnement Python

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install opencv-python mediapipe numpy pillow
```

> **Notes** :  
> - Sur certaines plateformes, MediaPipe requiert des versions précises de Python/NumPy.  
> - Sur Windows, installez les Visual C++ Build Tools si nécessaire.  
> - Tkinter n’est requis que si vous avez une UI (non indispensable ici).

---

## 4) Utilisation rapide (Quickstart)

### 4.1 Démo analyse en direct
```bash
source .venv/bin/activate
python analyse_posture.py
```
- Ouvre la webcam par défaut (`/dev/video0` sous Linux).  
- Affiche le flux avec **squelettisation** MediaPipe et overlay (si présent).  
- Calcule des **angles** (ex. épaule/bras/tronc) et **indicateurs**.

### 4.2 Mode enregistrement headless
```bash
source .venv/bin/activate
python recording.py
```
- Capture sans interface ; idéal pour batch/tests de perf.  
- Renseignez les chemins de sortie et options (si disponibles dans le script).

---

## 5) Intégration TMS / DUER (résumé)

Le projet peut produire des **indicateurs utiles** à la prévention des **TMS** :

| Facteur | Indicateur | Exemple de réglage |
|---|---|---|
| Postures hors zone | % du temps au‑delà d’un **seuil angulaire** (épaule, tronc, coude, poignet…) | `shoulder_abd=60°`, `trunk_flex=20°` |
| Répétitivité | **Cycles/min** (mouvement récurrent détecté) | `window=60s`, amplitude minimale |
| Durée d’exposition | Temps cumulé d’exposition par quart de travail | `warn=10%`, `alert=20%` |
| Efforts (proxy) | Vitesse/accélération angulaire, amplitude | `max_deg_s` |
| Environnement | Qualité d’image (éclairage/contraste) | `brightness_min`, `sharpness_min` |

**Export conseillé** : CSV/JSON par *poste/unité de travail* avec : date, durée totale, % exposition par articulation, cadence, événements “hors zone”.

---

## 6) Configuration (exemple YAML)

Vous pouvez externaliser vos seuils/paramètres dans un fichier YAML (à parser au démarrage) :

```yaml
thresholds:
  angles:
    shoulder_abd: 60
    trunk_flex: 20
  exposure:
    warn_pct: 10
    alert_pct: 20
cadence:
  window_s: 60
  min_cycle_amplitude: 10
quality:
  brightness_min: 0.2
  sharpness_min: 50
export:
  csv: true
  json: true
```

---

## 7) Architecture logicielle (suggestion)

- `estimateur_posture.py` : **purement fonctionnel**, calcule angles/indicateurs à partir des landmarks.  
- `analyse_posture.py` : **orchestration** : acquisition vidéo + MediaPipe + affichage/overlay + appels à l’estimateur.  
- `recording.py` : **runner** sans UI (logique de boucle, choix des formats d’export).

> Séparation claire = tests plus simples, réutilisation dans d’autres apps (ex. *Dernière‑Main* GUI/service).

---

## 8) Tests rapides

- Vérifier la détection : main levée, flexion tronc, abduction épaule.  
- Contrôler les valeurs d’angle affichées/loguées vs geste réel.  
- Ajuster les seuils dans le YAML jusqu’à un **bon compromis** sensibilité/spécificité.

---

## 9) Dépannage

- **Caméra introuvable** : `v4l2-ctl --list-devices` (Linux), test avec `ffplay /dev/video0`.  
- **ImportError mediapipe/opencv** : `pip show mediapipe opencv-python`, versions Python/wheels.  
- **Performance** : réduire la résolution d’entrée, traiter **1 image sur N**, limiter les tracés.

---

## 10) Licence & crédits

- **Licence :** à définir (MIT/Apache-2.0/GPLv3…).  
- **Crédits** : MediaPipe, OpenCV, NumPy, Pillow.

---

## 11) Intégration avec *Dernière‑Main* (optionnel)

Si vous utilisez *Dernière‑Main* pour l’UI/service :  
- Remplacer l’estimateur interne par `estimateur_posture.py`.  
- Réutiliser `analyse_posture.py` comme “module posture”.  
- Conserver `recording.py` pour le mode headless, et *Dernière‑Main* pour l’UI + exports/DUER.

