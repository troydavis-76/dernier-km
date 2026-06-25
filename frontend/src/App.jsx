import { useState, useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// -- Petits utilitaires ------------------------------------------------------
function toMin(hhmm) {
  const [h, m] = hhmm.split(':').map(Number)
  return h * 60 + m
}
function clientVide() {
  return { adresse: '', colis: 2, debut: '09:00', fin: '17:00' }
}

// -- La carte (Leaflet en direct, sans wrapper) ------------------------------
function Carte({ resultat }) {
  const conteneur = useRef(null)
  const carte = useRef(null)
  const couche = useRef(null)

  // Initialisation unique de la carte.
  useEffect(() => {
    if (carte.current) return
    const map = L.map(conteneur.current).setView([49.49, 0.107], 13)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap, © CARTO',
      maxZoom: 20,
    }).addTo(map)
    couche.current = L.layerGroup().addTo(map)
    carte.current = map
    // Leaflet a parfois besoin qu'on lui rappelle sa taille apres le rendu.
    setTimeout(() => map.invalidateSize(), 0)
    const surResize = () => map.invalidateSize()
    window.addEventListener('resize', surResize)
    return () => window.removeEventListener('resize', surResize)
  }, [])

  // Mise a jour des marqueurs et traces quand un resultat arrive.
  useEffect(() => {
    const map = carte.current
    const groupe = couche.current
    if (!map || !groupe || !resultat) return
    groupe.clearLayers()
    const points = []

    const d = resultat.depot
    L.circleMarker([d.lat, d.lon], {
      radius: 9, color: '#161D2B', weight: 3, fillColor: '#161D2B', fillOpacity: 1,
    })
      .bindPopup(`<b>Dépôt</b><br>${d.adresse}`)
      .addTo(groupe)
    points.push([d.lat, d.lon])

    resultat.tournees.forEach((t) => {
      if (t.trace && t.trace.length) {
        L.polyline(t.trace, { color: t.couleur, weight: 5, opacity: 0.85 }).addTo(groupe)
        t.trace.forEach((p) => points.push(p))
      }
      t.etapes.forEach((e) => {
        L.circleMarker([e.lat, e.lon], {
          radius: 8, color: '#ffffff', weight: 2, fillColor: t.couleur, fillOpacity: 1,
        })
          .bindPopup(
            `<b>Camion ${t.vehicule} — arrêt ${e.ordre}</b><br>${e.adresse}<br>` +
              (e.arrivee ? `Arrivée ${e.arrivee} · ` : '') +
              `${e.colis} colis`,
          )
          .addTo(groupe)
        points.push([e.lat, e.lon])
      })
    })

    if (points.length) map.fitBounds(points, { padding: [40, 40] })
    setTimeout(() => map.invalidateSize(), 0)
  }, [resultat])

  return <div ref={conteneur} className="carte" />
}

// -- L'application -----------------------------------------------------------
export default function App() {
  const [depot, setDepot] = useState({ adresse: '', debut: '08:00', fin: '18:00' })
  const [clients, setClients] = useState([
    { adresse: '', colis: 4, debut: '09:00', fin: '11:00' },
    { adresse: '', colis: 6, debut: '08:30', fin: '10:30' },
  ])
  const [nbCamions, setNbCamions] = useState(2)
  const [capacite, setCapacite] = useState(15)
  const [tempsService, setTempsService] = useState(5)
  const [creneaux, setCreneaux] = useState(true)
  const [apiUrl, setApiUrl] = useState('http://127.0.0.1:8000')
  const [reglages, setReglages] = useState(false)
  const [chargement, setChargement] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [resultat, setResultat] = useState(null)

  function majClient(i, champ, valeur) {
    setClients((cs) => cs.map((c, idx) => (idx === i ? { ...c, [champ]: valeur } : c)))
  }

  async function optimiser() {
    setErreur(null)
    if (!depot.adresse.trim()) {
      setErreur('Renseigne l’adresse du dépôt.')
      return
    }
    if (clients.length === 0 || clients.some((c) => !c.adresse.trim())) {
      setErreur('Chaque client doit avoir une adresse.')
      return
    }

    const adresses = [depot.adresse, ...clients.map((c) => c.adresse)]
    const demandes = [0, ...clients.map((c) => Number(c.colis) || 0)]
    const capacites = Array.from({ length: Number(nbCamions) || 1 }, () => Number(capacite) || 1)
    const fenetres = creneaux
      ? [
          [toMin(depot.debut), toMin(depot.fin)],
          ...clients.map((c) => [toMin(c.debut), toMin(c.fin)]),
        ]
      : null

    setChargement(true)
    setResultat(null)
    try {
      const reponse = await fetch(`${apiUrl}/api/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          adresses,
          demandes,
          capacites,
          fenetres,
          temps_service: Number(tempsService) || 0,
        }),
      })
      if (!reponse.ok) {
        const data = await reponse.json().catch(() => ({}))
        throw new Error(data.detail || `Erreur ${reponse.status}`)
      }
      setResultat(await reponse.json())
    } catch (e) {
      setErreur(
        e.message === 'Failed to fetch'
          ? `Impossible de joindre l’API (${apiUrl}). Vérifie qu’elle tourne.`
          : e.message,
      )
    } finally {
      setChargement(false)
    }
  }

  const totalColis = clients.reduce((s, c) => s + (Number(c.colis) || 0), 0)
  const capaciteTotale = (Number(nbCamions) || 0) * (Number(capacite) || 0)

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">Tournées</span>
        </div>
        <span className="tagline">Optimiseur de livraison · dernier kilomètre</span>
      </header>

      <main className="layout">
        {/* ---- Panneau de saisie ---- */}
        <section className="panel">
          <div className="bloc">
            <h2 className="titre">Dépôt</h2>
            <input
              className="champ"
              placeholder="Adresse de départ des camions"
              value={depot.adresse}
              onChange={(e) => setDepot({ ...depot, adresse: e.target.value })}
            />
            {creneaux && (
              <div className="horaires">
                <span className="horaires-label">Ouvert</span>
                <input type="time" className="heure" value={depot.debut}
                  onChange={(e) => setDepot({ ...depot, debut: e.target.value })} />
                <span className="horaires-sep">→</span>
                <input type="time" className="heure" value={depot.fin}
                  onChange={(e) => setDepot({ ...depot, fin: e.target.value })} />
              </div>
            )}
          </div>

          <div className="bloc">
            <div className="titre-rang">
              <h2 className="titre">Clients</h2>
              <span className="compteur">{clients.length}</span>
            </div>

            {clients.map((c, i) => (
              <div className="client" key={i}>
                <div className="client-tete">
                  <span className="client-num">Client {i + 1}</span>
                  <button className="lien-retirer" onClick={() => setClients((cs) => cs.filter((_, idx) => idx !== i))}>
                    Retirer
                  </button>
                </div>
                <input
                  className="champ"
                  placeholder="Adresse du client"
                  value={c.adresse}
                  onChange={(e) => majClient(i, 'adresse', e.target.value)}
                />
                <div className="client-bas">
                  <label className="mini">
                    Colis
                    <input type="number" min="0" className="petit" value={c.colis}
                      onChange={(e) => majClient(i, 'colis', e.target.value)} />
                  </label>
                  {creneaux && (
                    <div className="horaires">
                      <input type="time" className="heure" value={c.debut}
                        onChange={(e) => majClient(i, 'debut', e.target.value)} />
                      <span className="horaires-sep">→</span>
                      <input type="time" className="heure" value={c.fin}
                        onChange={(e) => majClient(i, 'fin', e.target.value)} />
                    </div>
                  )}
                </div>
              </div>
            ))}

            <button className="bouton-ajout" onClick={() => setClients((cs) => [...cs, clientVide()])}>
              + Ajouter un client
            </button>
          </div>

          <div className="bloc">
            <h2 className="titre">Camions</h2>
            <div className="duo">
              <label className="mini">
                Nombre
                <input type="number" min="1" className="petit" value={nbCamions}
                  onChange={(e) => setNbCamions(e.target.value)} />
              </label>
              <label className="mini">
                Capacité / camion
                <input type="number" min="1" className="petit" value={capacite}
                  onChange={(e) => setCapacite(e.target.value)} />
              </label>
            </div>
            <p className={`note ${totalColis > capaciteTotale ? 'note-alerte' : ''}`}>
              {totalColis} colis à livrer · {capaciteTotale} de capacité totale
              {totalColis > capaciteTotale ? ' — capacité insuffisante' : ''}
            </p>
          </div>

          <label className="interrupteur">
            <input type="checkbox" checked={creneaux} onChange={(e) => setCreneaux(e.target.checked)} />
            <span>Utiliser des créneaux horaires</span>
          </label>

          <button className="reglages-lien" onClick={() => setReglages(!reglages)}>
            {reglages ? '▾' : '▸'} Réglages avancés
          </button>
          {reglages && (
            <div className="bloc bloc-avance">
              <label className="mini">
                Temps de service par arrêt (min)
                <input type="number" min="0" className="petit" value={tempsService}
                  onChange={(e) => setTempsService(e.target.value)} />
              </label>
              <label className="mini">
                Adresse de l’API
                <input className="champ" value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} />
              </label>
            </div>
          )}

          <button className="cta" onClick={optimiser} disabled={chargement}>
            {chargement ? 'Optimisation…' : 'Optimiser les tournées'}
          </button>
          {erreur && <p className="erreur">{erreur}</p>}
        </section>

        {/* ---- Espace carte + résultats ---- */}
        <section className="espace">
          <div className="carte-zone">
            <Carte resultat={resultat} />
            {!resultat && !chargement && (
              <div className="voile">
                <p className="voile-titre">La carte attend tes adresses</p>
                <p className="voile-texte">
                  Renseigne le dépôt et les clients, puis lance l’optimisation pour voir les tournées tracées sur les rues.
                </p>
              </div>
            )}
            {chargement && (
              <div className="voile">
                <p className="voile-titre">Calcul en cours…</p>
                <p className="voile-texte">Géocodage des adresses, temps de trajet, puis optimisation.</p>
              </div>
            )}
          </div>

          {resultat && (
            <div className="resultats">
              {resultat.tournees.map((t) => (
                <article className="route" key={t.vehicule} style={{ borderLeftColor: t.couleur }}>
                  <header className="route-tete">
                    <span className="pastille" style={{ background: t.couleur }} />
                    <span className="route-titre">Camion {t.vehicule}</span>
                    <span className="route-colis">{t.total_colis} colis</span>
                  </header>
                  <ol className="arrets">
                    {t.etapes.map((e) => (
                      <li className="arret" key={e.ordre}>
                        {e.arrivee && <span className="arret-heure">{e.arrivee}</span>}
                        <span className="arret-adresse">{e.adresse}</span>
                        <span className="arret-colis">{e.colis}</span>
                      </li>
                    ))}
                  </ol>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
