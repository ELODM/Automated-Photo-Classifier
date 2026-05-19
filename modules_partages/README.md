# Modules partagés

Ce dossier contient les fichiers Python utilisés par **plusieurs phases** du pipeline, mutualisés ici pour éviter la duplication.

## Fichiers

| Fichier | Rôle |
|---|---|
| `config.py` | Constantes globales : URL de l'API Immich, clé API |
| `categories.py` | Définition des 15 catégories métier DREAL avec leur description et leur service responsable |

## Note sur la clé API

Dans le fichier `config.py`, la valeur de `API_KEY` a été remplacée par le placeholder `VOTRE_CLE_API_ICI`. Pour relancer le pipeline, il faut :
1. Générer une nouvelle clé API depuis l'interface Immich (paramètres du compte propriétaire des photos)
2. Remplacer `VOTRE_CLE_API_ICI` par la vraie clé


## Comment importer ces modules dans un script de phase

Les scripts originaux dans chaque phase utilisent un import direct comme :

```python
from config import API_KEY, IMMICH_URL
from categories import CATEGORIES
```

Lors du développement, `config.py` et `categories.py` étaient à côté des scripts. Pour les utiliser depuis un dossier de phase, il faut soit :
- Copier ces deux fichiers dans le dossier de la phase avant de lancer le script
- Soit modifier le `PYTHONPATH` pour inclure ce dossier `modules_partages/`
