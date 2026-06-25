"""
API d'optimisation de tournees (FastAPI).

Lancer en local :
    uvicorn main:app --reload

Puis ouvre http://127.0.0.1:8000/docs : une interface auto-generee te permet
de tester l'endpoint directement, sans frontend.
"""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import optimiseur

app = FastAPI(title="Optimisation de tournees de livraison")

# CORS : autorise l'interface React (sur un autre port/URL) a appeler l'API.
# En production, remplace ["*"] par l'URL exacte de ton frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DemandeOptimisation(BaseModel):
    adresses: List[str]                       # la 1ere = le depot
    demandes: Optional[List[int]] = None      # colis par adresse (depot = 0)
    capacites: Optional[List[int]] = None     # 1 valeur par vehicule
    fenetres: Optional[List[List[int]]] = None  # [[debut_min, fin_min], ...] ou absent
    temps_service: int = 5


@app.get("/")
def accueil():
    return {"message": "API d'optimisation de tournees. Va sur /docs pour tester."}


@app.post("/api/optimize")
def optimize(req: DemandeOptimisation):
    if len(req.adresses) < 2:
        raise HTTPException(400, "Il faut au moins un depot + un client.")
    fenetres = [tuple(f) for f in req.fenetres] if req.fenetres else None
    try:
        return optimiseur.optimiser(
            adresses=req.adresses,
            demandes=req.demandes,
            capacites=req.capacites,
            fenetres=fenetres,
            temps_service=req.temps_service,
        )
    except (ValueError, RuntimeError) as e:
        # Adresse introuvable, pas de solution, erreur OSRM...
        raise HTTPException(400, str(e))
