# OGC API - Environmental Data Retrieval (EDR)

Pour le moment seulement pour les données maillées

## Installation :
### 1. Création environnement python
```
python3 -m venv python_env
source python_env/bin/activate
pip install -r requirements.txt
```
### 2. Configurer Apache2
Par exemple avec [modwsgi](https://modwsgi.readthedocs.io/en/master/), bien penser à mettre le chemin de l'environnement python

### 3. Mise en zarr des fichiers
Voir [xarray](https://docs.xarray.dev/en/stable/user-guide/io.html#zarr)
Exemple de code bientôt...

### 4. Ajout des zarr à la config
Modifier le fichier config.json