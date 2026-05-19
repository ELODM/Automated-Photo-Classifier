# Phase 1 — Audit du stock photo

## Objectif

Avant de pouvoir nettoyer ou classifier les photos, il faut **comprendre ce qu'on a** : combien de photos, quels formats, quels utilisateurs, quels albums déjà existants, quelles métadonnées (GPS, EXIF, dates) sont disponibles.

Cette phase produit un état des lieux complet du stock photo hébergé sur l'instance Immich de la DREAL.

## Script

| Script | Description |
|---|---|
| `01_inventaire.py` | Interroge la base PostgreSQL d'Immich (via `docker exec`) pour produire un inventaire complet du stock |

## Comment lancer

```bash
python3 01_inventaire.py
```

Le script affiche les statistiques en console et produit le rapport JSON dans `resultats/rapport_inventaire.json`.

## Résultat obtenu (voir `resultats/`)

| Fichier | Contenu |
|---|---|
| `rapport_inventaire.json` | Compteurs globaux : nb d'assets, images, vidéos, fichiers avec GPS, avec date EXIF |

## Pourquoi PostgreSQL et pas l'API ?

L'API REST d'Immich v2.5.6 (version installée sur le serveur DREAL) a plusieurs endpoints qui retournent des erreurs 500 ou des résultats incomplets, notamment ceux liés aux statistiques globales. Les requêtes SQL directes via `docker exec immich_postgres psql` sont la solution la plus fiable pour ce projet.

## Conclusions de cette phase

L'audit a révélé :
- Un stock initial volumineux contenant beaucoup de **fichiers parasites** (vignettes système, GIF de l'interface, fichiers de cache)
- Une **absence majoritaire de métadonnées GPS** dans les photos
- Des **albums existants** créés par les utilisateurs DREAL

→ Ces constats ont motivé la **phase 2 de nettoyage** avant toute tentative de classification.
