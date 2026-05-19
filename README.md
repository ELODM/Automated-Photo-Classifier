# Photo-IA — Classification automatique de photos pour la DREAL Corse

**Auteure :** Salma EL-ODMI
**Formation :** Licence 3 Informatique — Université de Corse
**Lieu du stage :** DREAL Corse (Direction Régionale de l'Environnement, de l'Aménagement et du Logement) — Ajaccio
**Service :** ULI/SCIL
**Tuteur entreprise :** Pierre-Ange Martos (Chef ULI/SCIL)
**Tuteur pédagogique :** Florian Guéniot (UMR CNRS 6240 LISA)
**Période :** Avril 2026

---

## Présentation

Photo-IA est un pipeline automatisé qui classifie le stock de photos naturalistes de la DREAL Corse, hébergé sur une instance Immich.

Le pipeline est organisé en **4 phases**, chacune dans son propre dossier :

| Phase | Dossier | Rôle |
|---|---|---|
| Phase 1 | `phase1_audit/` | Audit du stock photo |
| Phase 2 | `phase2_nettoyage/` | Nettoyage des fichiers parasites, doublons, photos floues |
| Phase 3 | `phase3_veille_ia/` | Veille technologique et choix du modèle d'IA |
| Phase 4 | `phase4_production/` | Classification en production sur tout le stock |

Le dossier `modules_partages/` contient les fichiers utilisés par plusieurs phases (`config.py`, `categories.py`).

Chaque dossier de phase contient :
- Les **scripts Python** de la phase
- Un sous-dossier `resultats/` avec les **fichiers JSON / logs** produits par ces scripts pendant l'exécution réelle sur le serveur DREAL
- Un **README** qui détaille la phase

---

## Pipeline complet

```
[Stock photos Immich ~83 000 fichiers initialement]
            │
            ▼
   ═══════ PHASE 1 : AUDIT ═══════
   01_inventaire.py
            │
            ▼
   ═══════ PHASE 2 : NETTOYAGE ═══════
   Détection parasites + doublons + corrompus + photos floues
   3 itérations (v1, v2, v3) puis suppression
            │
            ▼ ~100 740 fichiers supprimés
            │
   ═══════ PHASE 3 : VEILLE IA ═══════
   Benchmark de plusieurs modèles d'IA
   MobileNetV3 (rejeté) / Moondream (rejeté) / LLaVA 7b (rejeté) / LLaVA-Phi3 3.8b (retenu)
            │
            ▼
   ═══════ PHASE 4 : PRODUCTION ═══════
   Classification de ~6 139 photos en 15 catégories métier
   Création automatique d'albums Immich
            │
            ▼
   [15 albums Photo-IA + 1 album "À vérifier" dans Immich]
```

---

## Stack technique

- **Langage :** Python 3.12
- **Vision par ordinateur :** OpenCV (Laplacien, Sobel, FFT), Pillow, NumPy
- **Modèle d'IA retenu :** LLaVA-Phi3 3.8b via Ollama (port 11435)
- **Gestionnaire de photos :** Immich v2.5.6 (4 conteneurs Docker + PostgreSQL + Redis)
- **Serveur :** VM Ubuntu 24.04 sur Proxmox — 18 CPU, 64 Go RAM, ~500 Go disque, sans GPU
- **Accès BDD :** requêtes PostgreSQL directes via `docker exec` (l'API REST d'Immich v2.5.6 ayant plusieurs endpoints non fonctionnels)

---

## Pour relancer le pipeline

> Le code a été développé pour le serveur DREAL et utilise des chemins et configurations spécifiques (Immich, Ollama). Pour relancer ce pipeline ailleurs, il faut adapter `modules_partages/config.py` à l'environnement cible.

1. Installer les dépendances : `opencv-python`, `Pillow`, `numpy`, `requests`, et `tensorflow` pour le test MobileNet
2. Renseigner la clé API Immich dans `modules_partages/config.py` (remplacer `VOTRE_CLE_API_ICI`)
3. Vérifier que les conteneurs Docker Immich tournent et qu'Ollama répond sur le port 11435 avec le modèle `llava-phi3:3.8b` chargé
4. Lancer les scripts phase par phase dans l'ordre, en lisant le README de chaque phase

---

## Résultats obtenus

- **~100 740 fichiers parasites** supprimés lors de la phase 2 (validés par Pierre-Ange Martos avant exécution réelle)
- **~6 139 photos** classifiées automatiquement par LLaVA-Phi3
- **15 albums Photo-IA** créés dans Immich, un par catégorie métier DREAL
- **1 album "À vérifier"** pour les classifications de confiance < 0,70

Le détail des chiffres est dans les fichiers JSON présents dans chaque dossier `resultats/`.

---

## Note sur la clé API

La clé API Immich qui figurait en dur dans certains scripts a été remplacée par le placeholder `VOTRE_CLE_API_ICI`. Aucune clé valide n'est versionnée dans ce livrable.
