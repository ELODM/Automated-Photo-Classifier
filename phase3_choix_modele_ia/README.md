# Phase 3 — Choix du modèle d'IA

## Objectif

Avant de lancer la classification en production, il fallait **choisir le bon modèle d'IA**. Cette phase a consisté à tester plusieurs modèles de vision sur des échantillons de photos DREAL et à comparer leurs performances (vitesse, stabilité, pertinence des résultats sur les catégories métier).

## Modèles testés

| Modèle | Type | Verdict | Raison |
|---|---|---|---|
| **MobileNetV3** | Classifieur ImageNet (1000 classes) | ❌ **Rejeté** | 339/500 photos avec confiance < 30%. Conçu pour reconnaître des **objets**, pas des **catégories abstraites** (littoral, zone humide, paysage...) |
| **LLaVA 7b** | Vision-langage multimodal | ❌ **Rejeté** | Trop lent (~250 s/photo sans GPU) |
| **Moondream** | Vision-langage léger | ❌ **Rejeté** | Sorties instables, format JSON non respecté |
| **LLaVA-Phi3 3.8b** | Vision-langage multimodal | ✅ **RETENU** | Stable, ~116 s/photo, taux de confiance correct sur les 15 catégories DREAL |

## Architecture nécessaire : "décrire-puis-classer"

Une leçon clé de cette phase : les modèles **classifieurs d'objets** (comme MobileNetV3 entraîné sur ImageNet) ne conviennent pas pour ce projet, parce que les catégories DREAL sont **abstraites** (littoral, montagne, zone humide, paysage...) et pas des objets simples.

Le projet nécessite plutôt une approche **vision-langage** : le modèle d'abord *décrit* la photo en mots, puis *classe* la description dans une catégorie. Cette approche est ce que font les modèles **LLaVA** et **Moondream**.

## Scripts

### Tests principaux
| Script | Modèle | Description |
|---|---|---|
| `10_classification.py` | MobileNetV3 | Test sur 500 photos. **Rejeté** suite à ce test |
| `13_test_llava_echantillon.py` | LLaVA-Phi3 | Test sur 15 photos variées du stock |
| `14_test_phase3_validation.py` | LLaVA-Phi3 | Validation finale avant production |

### Tests d'exploration (scripts ponctuels développés pendant la veille)
| Script | Sujet |
|---|---|
| `test_comparatif.py` | Comparaison côte-à-côte de plusieurs modèles |
| `test_immich.py` | Vérification de l'API Immich et de la clé |
| `test_moondream_seul.py` | Test isolé de Moondream |
| `test_moondream_format.py` | Tests de formats de prompt avec Moondream |
| `test_phi3.py` | Test de Phi3 (texte seul) |
| `test_phi3_5photos.py` | Test de LLaVA-Phi3 sur 5 photos |
| `test_optimisation.py` | Réglage des paramètres Ollama (température, format JSON) |
| `test_rapide.py` | Petits tests pendant le développement |

## Comment lancer le test du modèle retenu

```bash
python3 13_test_llava_echantillon.py
```

## Résultats obtenus (voir `resultats/`)

| Fichier | Contenu |
|---|---|
| `rapport_classification.json` | Résultats du test MobileNetV3 (montre pourquoi il a été rejeté) |
| `test_llava_echantillon.json` | Résultats LLaVA-Phi3 sur 15 photos variées |
| `test_phi3_5photos.json` | Résultats LLaVA-Phi3 sur 5 photos |

## Conclusion de la phase

**Modèle retenu pour la production : LLaVA-Phi3 3.8b**, accessible via Ollama sur le port 11435 avec l'image Docker `mdelapenya/llava-phi3:latest-3.8b`.

Paramètres optimisés (cf. `test_optimisation.py`) :
- `temperature = 0.1` (réponses stables)
- `format = "json"` (sortie structurée)
- `stream = False`

→ Voir `phase4_production/` pour la mise en production sur l'ensemble du stock.
