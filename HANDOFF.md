# HANDOFF — Session 3bc0cbae (05-06/11/2026)

## Travail effectué

### 1. Remise en service + basic auth Traefik
- Le service était down (Traefik `enable=false` depuis sept. 2026, décision sécurité C42)
- Basic auth Traefik mise en place, identifiants dans 1Password (`Dev - Claude / Scraping Belgique - Basic Auth`)
- Secrets CBEAPI migrés de `.env` (clair, supprimé) vers 1Password (`Scraping Belgique - CBEAPI`) + `.env.op`

### 2. Fix parser KBO
- Le tableau KBO a 6 colonnes, le parser en lisait 4 — noms, BCE, adresses étaient décalés
- Corrigé : extraction du nom depuis `td.benaming`, BCE depuis le lien `<a>`, adresse depuis cells[5]

### 3. Recherche par province
- La recherche NACE exige un code postal — impossible de chercher sans lieu
- Ajout du mapping provinces → plages de codes postaux (pas de 50, itéré par batch de 4)
- Validation frontend (alerte info) + backend (erreur 400 si pas de lieu)

### 4. Optimisation enrichissement email
- Ajout de Google Maps comme stratégie prioritaire (rapide, trouve aussi tel/site web)
- Délais réduits pour le crawl de sites (0.5-1.5s), augmentés pour Google (3-8s)
- Distribution de délais gamma (human-like) au lieu d'uniforme
- Gestion 429 + CAPTCHA sur Google Maps et Google Search
- Auto-download CSV + popup de fin à la complétion

### 5. Fix déploiement
- Le docker-compose.yml téléchargeait une archive statique (catbox.moe) au lieu de cloner GitHub
- Corrigé : `git clone -b main` (la branche par défaut GitHub est `master`, le code est sur `main`)

### 6. Enquête docker logs orphelins (incident 06/11/2026)
- **Origine confirmée : cette session (3bc0cbae)**, deux appels `docker logs` via SSH PowerShell
- Les timeouts côté outil (20s, 30s) ont tué le client local mais PAS le processus serveur
- Les processus sont restés orphelins (parent pid 1) et ont causé 201% CPU sur dockerd après recréation du container
- **Correctif : règle ajoutée au CLAUDE.md** — toujours `timeout X` côté serveur, jamais `-f`, options SSH de garde
- Aucun `docker logs` dans le code du dépôt — problème uniquement ad hoc

## Commits poussés
- `b4c7610` feat: add Traefik basic auth and migrate secrets to 1Password
- `871b959` fix: repair KBO parser and add province-wide NACE search
- `b277dfe` feat: add Google Maps as primary email source and optimize enrichment
- `b127054` fix: increase Google rate limits and add CAPTCHA detection
- `7bab3ba` feat: use human-like delay distribution to avoid bot detection
- `28e002e` feat: auto-download CSV and show completion popup

## Points d'attention pour la suite
- La branche par défaut sur GitHub est `master` mais tout le code est sur `main` — envisager de changer le default
- L'enrichissement ne trouve pas beaucoup de contacts (0 tel/email/site pour les agences de pub à Liège) — les sources Pages d'Or et CBEAPI retournent peu pour ce secteur
- Google Maps en scraping reste un risque de ban à long terme sur l'IP fixe du VPS
