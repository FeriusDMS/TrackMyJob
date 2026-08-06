# TrackMyJob

Bot automatique : lit tes emails Gmail, détecte les réponses aux candidatures **et** les nouvelles offres correspondant à tes alertes HelloWork/Indeed, envoie une notification Discord pour chaque.

Tourne toutes les 30 min via GitHub Actions — gratuit, zéro serveur.

---

## Setup (15 min)

### 1. Discord — Créer le webhook

1. Ouvre ton serveur Discord → channel de ton choix
2. Paramètres du channel → **Intégrations** → **Webhooks** → **Nouveau webhook**
3. Copie l'URL du webhook (tu en auras besoin à l'étape 4)

---

### 2. Google Cloud — Activer l'API Gmail

1. Va sur [console.cloud.google.com](https://console.cloud.google.com)
2. Crée un nouveau projet (ex: `TrackMyJob`)
3. **APIs & Services** → **Bibliothèque** → cherche `Gmail API` → **Activer**
4. **APIs & Services** → **Identifiants** → **Créer des identifiants** → **ID client OAuth 2.0**
   - Type d'application : **Application de bureau**
   - Nom : `TrackMyJob`
5. Télécharge le fichier JSON → renomme-le `client_secrets.json` → place-le dans `setup/`
6. **Écran de consentement OAuth** → ajoute ton email Gmail comme **Utilisateur test**

---

### 3. Obtenir le refresh token

```bash
pip install google-auth-oauthlib
python setup/get_token.py
```

Un navigateur s'ouvre → connecte-toi avec ton compte Gmail → accepte les permissions.

Le script affiche les 4 valeurs à copier.

---

### 4. GitHub — Ajouter les secrets

Dans ton repo GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** :

| Nom | Valeur |
|-----|--------|
| `GMAIL_CLIENT_ID` | affiché par le script |
| `GMAIL_CLIENT_SECRET` | affiché par le script |
| `GMAIL_REFRESH_TOKEN` | affiché par le script |
| `DISCORD_WEBHOOK_URL` | ton URL webhook Discord |

---

### 5. Configurer les alertes HelloWork et Indeed

Le bot ne fait aucun scraping : il lit les emails d'alerte que **toi** tu configures directement sur les sites, avec tes filtres.

**HelloWork** ([hellowork.com](https://www.hellowork.com)) :
1. Lance une recherche : mots-clés `Développeur Full Stack OR Développeur IA`, lieu `Saint-Malo, Rennes, Brest`, télétravail : ouvert au distanciel/présentiel, salaire minimum `36 000 €`
2. Active « Créer une alerte » sur la recherche, fréquence quotidienne, avec l'email Gmail suivi par le bot

**Indeed** ([indeed.fr](https://www.indeed.fr)) :
1. Même recherche : `Développeur Full Stack OR Développeur IA`, lieu `Saint-Malo / Rennes / Brest`, salaire minimum `36 000 €`, télétravail inclus
2. Clique « Recevoir des alertes emploi pour cette recherche », fréquence quotidienne, même email Gmail

⚠️ Le parsing du contenu des emails d'alerte est basé sur la structure HTML habituelle de ces sites. Si les notifications Discord arrivent avec des titres vides ou incohérents, c'est que le template a changé — il suffira d'ajuster `src/job_alerts.py`.

---

### 6. Activer GitHub Actions

Push le repo sur GitHub. Le workflow tourne automatiquement toutes les 30 min.

Pour tester immédiatement : **Actions** → **TrackMyJob** → **Run workflow**.

---

## Comment ça fonctionne

1. Récupère les emails de la boîte de réception non encore traités
2. Si l'email vient d'une alerte HelloWork/Indeed → extrait chaque offre du digest, ignore celles déjà vues (`data/seen_jobs.json`), notifie Discord pour les nouvelles
3. Sinon, si l'email est lié à une candidature (mots-clés FR + EN) → classifie : **Refus** / **Entretien** / **Offre** / **Accusé de réception** → notification Discord avec couleur selon la catégorie
4. Marque l'email avec le label Gmail `TrackMyJob/Processed` pour ne pas le retraiter
5. Committe `data/seen_jobs.json` s'il a changé, pour ne pas re-notifier les mêmes offres au prochain run

## Catégories détectées

| Catégorie | Couleur Discord | Exemples de mots-clés |
|-----------|----------------|----------------------|
| ❌ Refus | Rouge | malheureusement, unfortunately, not selected |
| 📅 Entretien | Vert | entretien, interview, disponibilité, schedule |
| 🎉 Offre | Or | félicitations, job offer, we would like to offer |
| 📬 Accusé | Bleu | bien reçu, received your application, under review |
| ❓ Inconnu | Gris | email lié au job mais non classifié |
| 🆕 Nouvelle offre | Violet | alerte HelloWork / Indeed correspondant à tes filtres |
