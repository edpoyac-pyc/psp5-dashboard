# Tableau de bord PSP5 en ligne

Ce dépôt génère le tableau de bord HTML avec `dashboard_psp5_live.py` et le publie sur GitHub Pages.

## Mise en ligne

1. Crée un dépôt GitHub, par exemple `psp5-dashboard`.
2. Envoie dans ce dépôt le fichier `dashboard_psp5_live.py` et le dossier `.github/workflows/` de ce projet.
3. Dans GitHub : **Settings → Pages → Build and deployment → Source → GitHub Actions**.
4. Ouvre l'onglet **Actions**, sélectionne « Actualiser et publier le tableau PSP5 », puis **Run workflow**.
5. À la fin du déploiement, GitHub affiche l'adresse du site dans le job et dans **Settings → Pages**.

Le workflow se relance ensuite chaque jour à 18 h UTC. Le lancement manuel reste possible depuis l'onglet Actions.

## Important sur les données

Le script fourni utilise des valeurs de secours si la récupération de justETF échoue ou si certains champs ne sont pas reconnus. Dans ce cas, le tableau affiche « valeurs de secours (mode hors ligne) » : les chiffres ne sont alors pas des cours actualisés. Vérifie que l'en-tête indique « justETF (récupéré en direct) » et consulte les champs manquants avant de te fier aux chiffres.

Le site GitHub Pages est public par défaut : toute personne ayant son URL peut le consulter. Ne place aucune donnée personnelle ou identifiant dans ce dépôt.
