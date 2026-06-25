"""
Moteur d'optimisation de tournees, refactorise pour etre appele par une API.
Aucune impression ici : tout est RENVOYE sous forme de donnees (dictionnaires),
prets a etre serialises en JSON et consommes par l'interface React.

C'est exactement la logique des scripts precedents, reorganisee en fonctions.
"""

import time
import requests
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

COULEURS = ["blue", "red", "green", "purple", "orange", "darkred"]


def hhmm(minutes):
    """Minutes-depuis-minuit -> '09h30'."""
    return f"{minutes // 60:02d}h{minutes % 60:02d}"


def geocoder(adresse):
    """Adresse -> (longitude, latitude) via Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": adresse, "format": "json", "limit": 1}
    headers = {"User-Agent": "livraison-app-abdoul"}
    r = requests.get(url, params=params, headers=headers, timeout=10)
    res = r.json()
    if not res:
        raise ValueError(f"Adresse introuvable : {adresse}")
    return float(res[0]["lon"]), float(res[0]["lat"])


def matrice_temps(coordonnees):
    """Matrice des temps de trajet en MINUTES entieres, via OSRM."""
    points = ";".join(f"{lon},{lat}" for lon, lat in coordonnees)
    url = f"https://router.project-osrm.org/table/v1/driving/{points}"
    r = requests.get(url, params={"annotations": "duration"}, timeout=20)
    data = r.json()
    if data.get("code") != "Ok":
        raise RuntimeError(f"Erreur OSRM (table) : {data.get('message', 'inconnue')}")
    return [
        [int(round(t / 60)) if t is not None else 10**6 for t in ligne]
        for ligne in data["durations"]
    ]


def geometrie_route(points):
    """Trace routier reel d'une tournee via OSRM (pour la carte).
    Renvoie une liste de [lat, lon], ou None si indisponible."""
    coords = ";".join(f"{lon},{lat}" for lon, lat in points)
    url = f"https://router.project-osrm.org/route/v1/driving/{coords}"
    try:
        r = requests.get(url, params={"overview": "full", "geometries": "geojson"},
                         timeout=20)
        data = r.json()
        if data.get("code") != "Ok":
            return None
        return [[lat, lon] for lon, lat in data["routes"][0]["geometry"]["coordinates"]]
    except Exception:
        return None


def resoudre(matrice, demandes, capacites, fenetres, temps_service, depot=0):
    """Resout le VRP : capacite + creneaux horaires (optionnels).
    Renvoie une liste de tournees, chacune = liste de (noeud, heure_arrivee_min)."""
    nb_vehicules = len(capacites)
    manager = pywrapcp.RoutingIndexManager(len(matrice), nb_vehicules, depot)
    routing = pywrapcp.RoutingModel(manager)

    def cout_temps(i, j):
        a = manager.IndexToNode(i)
        b = manager.IndexToNode(j)
        service = 0 if a == depot else temps_service
        return matrice[a][b] + service

    idx_temps = routing.RegisterTransitCallback(cout_temps)
    routing.SetArcCostEvaluatorOfAllVehicles(idx_temps)

    # Capacite (colis)
    def demande(i):
        return demandes[manager.IndexToNode(i)]

    idx_demande = routing.RegisterUnaryTransitCallback(demande)
    routing.AddDimensionWithVehicleCapacity(idx_demande, 0, capacites, True, "Capacite")

    # Creneaux horaires (uniquement si fournis)
    dim = None
    if fenetres is not None:
        routing.AddDimension(idx_temps, 12 * 60, 24 * 60, False, "Temps")
        dim = routing.GetDimensionOrDie("Temps")
        for noeud, (debut, fin) in enumerate(fenetres):
            if noeud == depot:
                continue
            dim.CumulVar(manager.NodeToIndex(noeud)).SetRange(debut, fin)
        debut_d, fin_d = fenetres[depot]
        for v in range(nb_vehicules):
            dim.CumulVar(routing.Start(v)).SetRange(debut_d, fin_d)
        for v in range(nb_vehicules):
            routing.AddVariableMinimizedByFinalizer(dim.CumulVar(routing.Start(v)))
            routing.AddVariableMinimizedByFinalizer(dim.CumulVar(routing.End(v)))

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(params)
    if not solution:
        return None

    tournees = []
    for v in range(nb_vehicules):
        index = routing.Start(v)
        etapes = []
        while True:
            noeud = manager.IndexToNode(index)
            arrivee = solution.Min(dim.CumulVar(index)) if dim is not None else None
            etapes.append((noeud, arrivee))
            if routing.IsEnd(index):
                break
            index = solution.Value(routing.NextVar(index))
        tournees.append(etapes)
    return tournees


def optimiser(adresses, demandes=None, capacites=None, fenetres=None,
              temps_service=5, pause_geocodage=1.0):
    """Orchestrateur complet : adresses -> resultat JSON pret pour la carte.

    - adresses : liste, la 1ere = le depot.
    - demandes : colis par adresse (depot = 0). Defaut : 1 colis par client.
    - capacites : liste, 1 valeur par vehicule. Defaut : 1 vehicule.
    - fenetres : [[debut_min, fin_min], ...] par adresse, ou None (pas de creneaux).
    """
    n = len(adresses)
    depot = 0
    if demandes is None:
        demandes = [0] + [1] * (n - 1)
    if capacites is None:
        capacites = [sum(demandes)]

    # 1) Geocodage
    coordonnees = []
    for adresse in adresses:
        coordonnees.append(geocoder(adresse))
        time.sleep(pause_geocodage)   # limite Nominatim : 1 req/seconde

    # 2) Matrice des temps
    matrice = matrice_temps(coordonnees)

    # 3) Resolution
    tournees = resoudre(matrice, demandes, capacites, fenetres, temps_service, depot)
    if tournees is None:
        raise RuntimeError("Aucune solution : creneaux ou capacites trop serres.")

    # 4) Mise en forme du resultat pour le frontend
    lon0, lat0 = coordonnees[depot]
    resultat = {
        "depot": {"adresse": adresses[depot], "lat": lat0, "lon": lon0},
        "tournees": [],
    }
    for v, etapes in enumerate(tournees):
        noeuds = [noeud for (noeud, _) in etapes]
        etapes_json = []
        ordre = 0
        total_colis = 0
        for noeud, arrivee in etapes:
            if noeud == depot:
                continue
            ordre += 1
            total_colis += demandes[noeud]
            lon, lat = coordonnees[noeud]
            etapes_json.append({
                "ordre": ordre,
                "adresse": adresses[noeud],
                "lat": lat,
                "lon": lon,
                "colis": demandes[noeud],
                "arrivee": hhmm(arrivee) if arrivee is not None else None,
                "arrivee_min": arrivee,
            })
        # Trace routier (sinon lignes droites en secours)
        points = [coordonnees[nd] for nd in noeuds]
        trace = geometrie_route(points)
        if trace is None:
            trace = [[coordonnees[nd][1], coordonnees[nd][0]] for nd in noeuds]
        resultat["tournees"].append({
            "vehicule": v + 1,
            "couleur": COULEURS[v % len(COULEURS)],
            "total_colis": total_colis,
            "etapes": etapes_json,
            "trace": trace,
        })
    return resultat
