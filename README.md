# Tournées — Optimiseur de tournées de livraison

> Application web qui calcule des tournées de livraison optimales : on saisit
> des adresses, l'outil répartit les colis entre les véhicules, respecte les
> créneaux horaires de chaque client, et affiche les itinéraires sur une carte.

![Aperçu de l'application](images/apercu.png)

> _Remplace l'image ci-dessus par ta capture : crée un dossier `images/` à la
> racine et dépose-y ton fichier (par ex. `apercu.png`)._

---

## Le problème

La livraison du dernier kilomètre est le poste le plus coûteux de la chaîne
logistique. Pourtant, beaucoup de petites structures (commerces, producteurs,
artisans) planifient encore leurs tournées **à la main**, sur Google Maps ou un
tableur. Résultat : des kilomètres inutiles, du temps perdu, et des livraisons
mal ordonnées.

Trouver l'ordre de passage optimal pour plusieurs véhicules, avec des
contraintes réelles, est un problème mathématiquement difficile (le *Vehicle
Routing Problem*). Ce projet le résout et rend le résultat lisible sur une carte.

## Fonctionnalités

- **Optimisation multi-véhicules** — répartit automatiquement les arrêts entre
  les camions et minimise la distance totale.
- **Contrainte de capacité** — chaque véhicule a une limite de colis ; le
  solveur en tient compte.
- **Créneaux horaires** — chaque client peut être livré dans une plage horaire
  donnée (*VRPTW*) ; l'outil calcule l'heure d'arrivée de chaque arrêt.
- **Adresses réelles** — géocodage automatique des adresses en coordonnées GPS.
- **Temps de trajet réels** — distances et durées calculées sur le réseau
  routier, pas à vol d'oiseau.
- **Carte interactive** — itinéraires tracés sur les rues, marqueurs par
  véhicule, heures d'arrivée et nombre de colis par arrêt.

## Stack technique

| Couche       | Technologies                                             |
| ------------ | -------------------------------------------------------- |
| **Backend**  | Python, FastAPI, Google OR-Tools                         |
| **Frontend** | React, Vite, Leaflet                                     |
| **Données**  | OpenStreetMap — Nominatim (géocodage), OSRM (routage)    |

## Architecture

```
┌─────────────┐    HTTP / JSON     ┌──────────────────────┐
│    React     │ ─────────────────► │       FastAPI         │
│  + Leaflet   │ ◄───────────────── │   POST /api/optimize  │
└─────────────┘     tournées        └──────────┬───────────┘
                                               │
                   ┌───────────────────────────┼───────────────────────────┐
                   ▼                           ▼                           ▼
            ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
            │  Nominatim   │           │     OSRM     │           │  OR-Tools    │
            │  géocodage   │           │  temps de    │           │  solveur     │
            │              │           │  trajet      │           │  VRP / VRPTW │
            └──────────────┘           └──────────────┘           └──────────────┘
```

## Comment ça marche (le pipeline)

1. **Saisie** — l'utilisateur entre le dépôt, les clients, les colis et les
   créneaux dans l'interface React.
2. **Géocodage** — chaque adresse est convertie en coordonnées (Nominatim).
3. **Matrice des temps** — OSRM calcule les temps de trajet routiers entre tous
   les points, en une requête.
4. **Optimisation** — OR-Tools résout le problème sous contraintes de capacité
   et de créneaux, et renvoie les tournées.
5. **Affichage** — l'interface dessine les itinéraires sur la carte et liste les
   feuilles de route.

## Installation et lancement

### Structure du projet

```
optimiseur-tournees/
├── backend/
│   ├── main.py
│   ├── optimiseur.py
│   └── requirements.txt
├── frontend/          # le projet React (contenu de tournees-web)
└── README.md
```

### Prérequis

- Python 3.10+
- Node.js 18+

### 1. Backend (l'API)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

L'API tourne sur `http://127.0.0.1:8000`. Une interface de test
auto-générée est disponible sur `http://127.0.0.1:8000/docs`.

### 2. Frontend (l'interface)

Dans un second terminal :

```bash
cd frontend
npm install
npm run dev
```

Ouvre l'URL affichée (en général `http://localhost:5173`). L'adresse de l'API
se règle dans « Réglages avancés ».

## Pistes d'amélioration

- **Serveur OSRM auto-hébergé** pour ne plus dépendre du serveur public et
  traiter de gros volumes.
- **Notifications client** (e-mail / SMS) avec le créneau de livraison.
- **Suivi en temps réel** des tournées (dans le respect du cadre légal).
- **Export** des feuilles de route en PDF.

## Limites connues

- Le géocodage (Nominatim) et le routage (OSRM) utilisent les **serveurs
  publics d'OpenStreetMap**, limités en volume — adaptés à la démonstration et
  aux petits volumes, pas à une production intensive.
- La précision dépend de la qualité des adresses saisies (préférer des adresses
  complètes avec numéro de rue).

## Contexte

Projet conçu et développé en autodidacte, de la recherche opérationnelle
jusqu'à l'interface, pour résoudre un problème logistique concret de bout en bout.
