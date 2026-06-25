# Tournées — interface web

Interface React pour l'optimiseur de tournées. Elle collecte des adresses,
appelle l'API Python (`/api/optimize`), et affiche les tournées sur une carte.

## Prérequis

- **Node.js** installé (https://nodejs.org).
- **L'API backend** qui tourne (le projet `main.py` / `optimiseur.py`).
  Par défaut, l'interface l'attend sur `http://127.0.0.1:8000`.

## Lancer en local

```bash
npm install
npm run dev
```

Ouvre l'URL affichée (en général http://localhost:5173).

1. Renseigne l'adresse du **dépôt**.
2. Ajoute tes **clients** (adresse, colis, et créneau horaire si activé).
3. Règle le **nombre de camions** et la **capacité** par camion.
4. Clique sur **Optimiser les tournées**.

L'adresse de l'API se change dans **Réglages avancés** (utile une fois déployé).

## Construire pour la production

```bash
npm run build
```

Le site statique est généré dans le dossier `dist/`.

## Déploiement

- **Cette interface** → Vercel (import du dépôt, build `npm run build`,
  dossier de sortie `dist`).
- **L'API Python** → Render ou Railway (le serverless de Vercel est trop léger
  pour OR-Tools).
- Une fois l'API en ligne, mets son URL publique dans « Réglages avancés ».
