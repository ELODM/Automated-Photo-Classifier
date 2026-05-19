# Phase 4 — Classification en production

## Objectif

Lancer la classification automatique sur **l'ensemble du stock de photos** restant après le nettoyage de la phase 2, avec le modèle **LLaVA-Phi3 3.8b** retenu en phase 3.

Pour chaque photo, le pipeline :
1. Envoie l'image à LLaVA-Phi3 (via Ollama)
2. Récupère une description en français et une catégorie parmi les 15 catégories métier DREAL
3. Écrit la description dans `asset_exif.description` (visible sous la photo dans l'interface Immich)
4. Ajoute la photo à l'album correspondant à sa catégorie (création de l'album si nécessaire)
5. Si la confiance est inférieure au seuil de **0,70**, ajoute aussi la photo à l'album **"À vérifier"** pour validation par un agent DREAL

## Script

| Script | Description |
|---|---|
| `05_classification_production.py` | Script principal de classification en production (cœur métier du projet) |

## Fonctionnalités notables

- **Mode reprise automatique (idempotent)** : si le script s'arrête (Ctrl+C, perte de connexion, crash...), on peut le relancer et il reprendra exactement où il s'était arrêté grâce au fichier `fichiers_immich.json`
- **Cache des album_ids en mémoire** : évite un appel API par photo
- **Pas d'écriture JSON par photo** : Immich/PostgreSQL est la **source de vérité unique**. Ce choix corrige un bug de saturation disque (`OSError: [Errno 28] No space left on device`) rencontré dans une version antérieure du script
- **Log détaillé** : chaque photo traitée est loggée avec sa catégorie, confiance et temps de traitement
- **Statistiques périodiques** : tous les 50 photos, le script affiche la progression et l'heure estimée de fin

## Comment lancer

```bash
# Lancer dans un screen pour que le script survive aux déconnexions SSH
screen -S photo-ia
python3 05_classification_production.py
# Détacher le screen avec Ctrl+A puis D
```

Le script crée automatiquement les 15 albums Photo-IA dans Immich + un album "À vérifier".

## Catégories métier DREAL

Les 15 catégories utilisées sont définies dans `modules_partages/categories.py` :

1. **faune** — animaux sauvages
2. **flore** — plantes, arbres, végétation
3. **littoral** — côte, plage, falaises
4. **montagne** — pics, hauts massifs
5. **milieu_aquatique** — rivières, lacs, cours d'eau
6. **zone_humide** — marais, marécages
7. **paysage** — paysage général
8. **batiment** — bâtiments, constructions
9. **infrastructure** — routes, ponts, ports, transports
10. **pollution** — déchets, dégâts industriels
11. **aerien** — vues aériennes / satellite
12. **document** — documents numérisés, cartes
13. **portrait** — personnes
14. **energie** — lignes électriques, panneaux solaires, éoliennes
15. **risque_naturel** — incendies, inondations, glissements

## Résultats obtenus (voir `resultats/`)

| Fichier | Contenu |
|---|---|
| `classification_production.json` | Résultats de classification photo par photo (catégorie, description, confiance) |
| `classification_production.log` | Log complet de l'exécution (timestamps, progressions, erreurs éventuelles) |
| `fichiers_immich.json` | Liste des photos déjà traitées (utilisé pour la reprise automatique) |

## Chiffres clés

- **~6 139 photos** classifiées
- **15 albums Photo-IA** créés dans Immich
- **1 album "À vérifier"** pour les photos en basse confiance
- **~116 s/photo en moyenne** (sans GPU)

## Limites et perspectives

- Le temps de traitement reste élevé en l'absence de GPU sur le serveur. Une carte graphique permettrait de descendre à quelques secondes par photo.
- La boucle de feedback humain (corrections d'agents dans Immich → réentraînement) n'a pas été implémentée faute de temps, mais la donnée nécessaire est disponible dans Immich.
