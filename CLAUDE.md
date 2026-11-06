# Scrapping

## Description
Service de web scraping des professions en Belgique. Récupère les données des professionnels belges à partir de KBO/BCE, Pages d'Or et CBEAPI.

## Stack
- **Langage** : Python 3.12
- **Web** : Flask + Gunicorn
- **Scraping** : BeautifulSoup4, Requests, lxml
- **Data** : Pandas
- **Déploiement** : Docker sur VPS Hostinger (via Traefik)

## Structure
- `main.py` — Point d'entrée CLI
- `scrapers/` — Modules de scraping (KBO, Pages d'Or, CBEAPI, email, Pages Jaunes FR)
- `models.py` — Modèle `Professional` (dataclass)
- `enricher.py` — Pipeline d'enrichissement CLI (KBO → Pages d'Or → fusion → CBEAPI → email)
- `exporter.py` — Export CSV
- `config.py` — Configuration (URLs, délais, user agents)
- `location_utils.py` — Mapping ville→code postal belge + filtrage par localisation
- `nace_codes.py` / `nace_codes_fr.py` — Dictionnaire des codes NACE
- `web/` — Interface web Flask
  - `app.py` — Routes Flask
  - `web_enricher.py` — Pipeline d'enrichissement web (avec callback progression)
  - `job_manager.py` — Gestion des jobs asynchrones
  - `templates/` — Templates Jinja2
  - `static/` — CSS + JS

## Secrets
- **Gestion** : 1Password (coffre `Dev - Claude`), injectés via `op run --env-file=.env.op`
- **Items** :
  - `Scraping Belgique - Basic Auth` — identifiants Traefik basic auth (accès HTTPS public)
  - `Scraping Belgique - CBEAPI` — clés API CBEAPI (enrichissement entreprises)
- **Pas de `.env` en clair** — utiliser `.env.op` avec références `op://`

## Commandes locales
```bash
op run --env-file=.env.op -- python main.py --profession plombier --ville Bruxelles
op run --env-file=.env.op -- python main.py --profession avocat --province Liège --limit 50
python main.py --list-professions                             # Pas de secrets nécessaires
op run --env-file=.env.op -- python -m web.app                # Serveur web local
docker compose up -d                                          # Via Docker local
```

## Déploiement

### Infrastructure
- **VPS** : Hostinger `193.203.191.251` (srv767464.hstgr.cloud)
- **URL** : `https://scraping.srv767464.hstgr.cloud` (basic auth Traefik, creds dans 1Password)
- **Repo** : `github.com/laurent7850/scraping-belgique` (privé)
- **Container** : `scraping-belgique-web-1` (Python 3.12-slim)
- **Reverse proxy** : Traefik (réseau `root_default`)
- **Volume persistant** : `scraping_app:/app`

### Déployer une mise à jour
```bash
# 1. Commit et push
cd "C:\Users\laure\OneDrive\Documents\Claude code\Scrapping"
git add -A && git commit -m "fix: description" && git push

# 2. Redémarrer le container (le git pull se fait automatiquement au démarrage)
# Via Hostinger API / MCP ou via SSH :
ssh root@193.203.191.251
cd /docker/scraping-belgique && docker compose restart
```

### Fonctionnement du container
Au démarrage, le container :
1. Installe `git`
2. Si premier lancement : `git clone -b main` depuis GitHub
3. Sinon : `git pull origin main` (récupère les dernières modifications)
4. `pip install` des dépendances
5. Lance `python -m web.app`

### Commandes SSH vers le VPS — règles obligatoires
**Incident du 05/11/2026 :** deux `docker logs` lancés par SSH sans timeout serveur sont restés orphelins 24h sur le VPS après que le client SSH a été tué par le timeout outil. `dockerd` a atteint 201% CPU en relisant les logs supprimés en boucle.

**Règles à suivre systématiquement :**
- **Toujours `timeout` côté serveur** : `ssh rampa 'timeout 20 docker logs --tail 50 <conteneur>'`, jamais un `docker logs` nu
- **Jamais `-f`** (follow) dans un `docker logs` à distance
- **Toujours `--since`** pour borner : `timeout 20 docker logs --since 5m --tail 100 <conteneur>`
- **Options SSH de garde** : `-o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=2`
- **Préférer Git Bash** avec heredoc pour les commandes SSH complexes, pas PowerShell avec guillemets imbriqués

## Sources de données
| Source | Usage | Rate limit |
|--------|-------|------------|
| KBO/BCE | Recherche par NACE ou mot-clé | 1-3s entre requêtes |
| Pages d'Or | Enrichissement (tel, email, site, horaires) | 2-5s entre requêtes |
| CBEAPI | Enrichissement complémentaire | 2500 req/jour |
| Email enricher | Recherche email via site web + Google | 1.5-6s entre requêtes |

## Filtrage par localisation
Le module `location_utils.py` assure que les résultats correspondent à la ville demandée :
- **KBO** : résolution ville→code postal (KBO n'accepte que des codes postaux)
- **Post-filtrage** : après fusion, les résultats hors zone sont éliminés par code postal
- ~150 villes belges mappées (toutes les grandes villes + communes importantes)
