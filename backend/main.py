"""
API d'optimisation de tournées (FastAPI).

Lancer en local :
    uvicorn main:app --reload

Puis ouvre http://127.0.0.1:8000/docs : une interface auto-générée te permet
de tester l'endpoint directement, sans frontend.
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client  # <-- Nouveau : Import Supabase

import optimiseur

app = FastAPI(title="Optimisation de tournées de livraison")

# --- CONFIGURATION SUPABASE (SÉNÉGAL) ---
# 💻 Remplace ces valeurs par TES vraies clés récupérées sur ton tableau de bord Supabase
SUPABASE_URL = "https://fiqluuwsjrpqcrrpinsy.supabase.co/rest/v1/" 
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZpcWx1dXdzanJwcWNycnBpbnN5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODczMTgyOTUsImV4cCI6MjEwMjg5NDI5NX0.YZ6nrEZ1G5RsDBh7zyEpuMYMxtNrKROrujiVVVvmMCs"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# CORS : autorise l'interface React à appeler l'API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NOUVEAU MODÈLE POUR LE FORMULAIRE MARCHAND ---
class CommandeMarchand(BaseModel):
    nom_client: str
    telephone: str
    montant_cod: float
    moyen_paiement: str
    latitude: float
    longitude: float

# --- MODÈLES EXISTANTS ---
class DemandeOptimisation(BaseModel):
    adresses: List[str]                       # la 1ère = le dépot
    demandes: Optional[List[int]] = None      # colis par adresse (dépot = 0)
    capacites: Optional[List[int]] = None     # 1 valeur par véhicule
    fenetres: Optional[List[List[int]]] = None  # [[début_min, fin_min], ...] ou absent
    temps_service: int = 5


@app.get("/")
def accueil():
    return {"message": "API d'optimisation de tournées. Va sur /docs pour tester."}


# --- NOUVELLE ROUTE : RÉCEPTION DES COMMANDES MARCHANDS ---
@app.post("/api/commandes-attente")
def recevoir_commande_marchand(commande: CommandeMarchand):
    try:
        # Envoie les données saisies par la boutique Instagram directement dans la table Supabase
        data = supabase.table("commandes_attente").insert(commande.dict()).execute()
        return {"status": "success", "data": data.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")


# --- ROUTE EXISTANTE D'OPTIMISATION ---
@app.post("/api/optimize")
def optimize(req: DemandeOptimisation):
    if len(req.adresses) < 2:
        raise HTTPException(400, "Il faut au moins un dépot + un client.")
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
