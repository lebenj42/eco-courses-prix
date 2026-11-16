"""Prix réels relevés en magasin, tirés d'Open Prices (Open Food Facts).

Open Prices est une base ouverte de prix photographiés en rayon ou sur des
tickets par des bénévoles, dans toutes les enseignes françaises. Licence
ODbL : citer « Open Prices, contributeurs Open Food Facts » et garder
notre base de prix dérivée sous la même licence.

Sortie : un fichier JSON avec, par ingrédient, le prix bas courant (premier
quartile) au kilo, au litre ou à la pièce sur les 12 derniers mois en France, le nombre de
relevés et le même prix par enseigne. Usage : python3 tool/open_prices.py SORTIE
"""
import datetime as dt
import json
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

API = "https://prices.openfoodfacts.org/api/v1/prices"
PAGES = 3
# ingrédient -> (unité de l'ingrédient, type, étiquettes de catégorie à essayer)
CATEGORIES = {
    "pates": ("kg", "produit", ["en:pastas"]),
    "riz": ("kg", "produit", ["en:rices"]),
    "semoule": ("kg", "produit", ["en:durum-wheat-semolinas", "en:semolinas", "en:couscous"]),
    "lentilles": ("kg", "produit", ["en:lentils"]),
    "pois_chiches": ("kg", "produit", ["en:chickpeas"]),
    "haricots_rouges": ("kg", "produit", ["en:red-kidney-beans", "en:kidney-beans"]),
    "tomates_conc": ("kg", "produit", ["en:canned-tomatoes"]),
    "lait_coco": ("l", "produit", ["en:coconut-milks"]),
    "farine": ("kg", "produit", ["en:wheat-flours"]),
    "gnocchis": ("kg", "produit", ["en:gnocchi"]),
    "lait": ("l", "produit", ["en:semi-skimmed-milks"]),
    "creme": ("l", "produit", ["en:fresh-creams", "en:creams"]),
    "beurre": ("kg", "produit", ["en:butters"]),
    "emmental": ("kg", "produit", ["en:emmentaler", "en:emmental-cheese", "en:grated-cheese"]),
    "mozzarella": ("kg", "produit", ["en:mozzarella"]),
    "feta": ("kg", "produit", ["en:feta"]),
    "jambon": ("kg", "produit", ["en:white-hams"]),
    "lardons": ("kg", "produit", ["en:lardons"]),
    "poulet_filet": ("kg", "produit", ["en:chicken-breasts", "en:chicken-fillets"]),
    "boeuf_hache": ("kg", "produit", ["en:ground-beef", "en:beef-burgers"]),
    "saucisses": ("kg", "produit", ["en:sausages"]),
    "thon": ("kg", "produit", ["en:canned-tunas"]),
    "saumon": ("kg", "produit", ["en:salmons", "en:salmon-fillets"]),
    "epinards": ("kg", "produit", ["en:frozen-spinachs", "en:spinachs"]),
    "petits_pois": ("kg", "produit", ["en:frozen-peas", "en:garden-peas"]),
    "huile": ("l", "produit", ["en:sunflower-oils"]),
    "pdt": ("kg", "brut", ["en:potatoes"]),
    "carottes": ("kg", "brut", ["en:carrots"]),
    "oignons": ("kg", "brut", ["en:onions", "en:yellow-onions"]),
    "courgettes": ("kg", "brut", ["en:zucchini"]),
    "tomates": ("kg", "brut", ["en:tomatoes"]),
    "poivrons": ("kg", "brut", ["en:bell-peppers", "en:sweet-peppers"]),
    "poireaux": ("kg", "brut", ["en:leeks"]),
    "champignons": ("kg", "brut", ["en:mushrooms", "en:button-mushrooms"]),
    "potiron": ("kg", "brut", ["en:pumpkins", "en:squashes"]),
    "citron": ("piece", "brut", ["en:lemons"]),
    # Deuxième lot de recettes maison (tool/recettes_maison.py)
    "haricots_verts": ("kg", "produit", ["en:frozen-green-beans", "en:green-beans"]),
    "mais": ("kg", "produit", ["en:canned-sweet-corn", "en:sweet-corns"]),
    "haricots_blancs": ("kg", "produit", ["en:canned-white-beans", "en:white-beans"]),
    "lentilles_vertes": ("kg", "produit", ["en:green-lentils"]),
    "pois_casses": ("kg", "produit", ["en:split-peas"]),
    "polenta": ("kg", "produit", ["en:polentas", "en:cornmeals"]),
    "nouilles": ("kg", "produit", ["en:chinese-noodles", "en:noodles"]),
    "chevre": ("kg", "produit", ["en:goat-cheeses"]),
    "raclette": ("kg", "produit", ["en:raclette"]),
    "tofu": ("kg", "produit", ["en:tofu"]),
    "knacks": ("kg", "produit", ["en:strasbourg-sausages", "en:frankfurters"]),
    "merguez": ("kg", "produit", ["en:merguez"]),
    "dinde": ("kg", "produit", ["en:turkey-escalopes", "en:turkey-breasts"]),
    "cuisses_poulet": ("kg", "produit", ["en:chicken-legs", "en:chicken-thighs"]),
    "crevettes": ("kg", "produit", ["en:frozen-shrimps", "en:shrimps"]),
    "poisson_pane": ("kg", "produit", ["en:breaded-fish", "en:fish-fingers"]),
    "aubergines": ("kg", "brut", ["en:eggplants", "en:aubergines"]),
    "patate_douce": ("kg", "brut", ["en:sweet-potatoes"]),
    "endives": ("kg", "brut", ["en:endives", "en:chicory"]),
    "navets": ("kg", "brut", ["en:turnips"]),
    "brocoli": ("piece", "brut", ["en:broccoli"]),
    "chou_fleur": ("piece", "brut", ["en:cauliflowers"]),
    "salade": ("piece", "brut", ["en:lettuces"]),
    "ail": ("piece", "brut", ["en:garlic"]),
    # Troisième lot de recettes maison (tool/recettes_maison3.py)
    "betteraves": ("kg", "produit", ["en:cooked-beetroots", "en:beetroots"]),
    "olives": ("kg", "produit", ["en:black-olives", "en:olives"]),
    "anchois": ("kg", "produit", ["en:anchovy-fillets", "en:anchovies"]),
    "cornichons": ("kg", "produit", ["en:gherkins", "en:pickled-cucumbers"]),
    "pignons": ("kg", "produit", ["en:pine-nuts"]),
    "noix": ("kg", "produit", ["en:walnut-kernels", "en:walnuts"]),
    "cacahuetes": ("kg", "produit", ["en:roasted-peanuts", "en:peanuts"]),
    "raisins_secs": ("kg", "produit", ["en:raisins"]),
    "miel": ("kg", "produit", ["en:honeys"]),
    "mayonnaise": ("kg", "produit", ["en:mayonnaises"]),
    "pesto": ("kg", "produit", ["en:pestos", "en:green-pestos"]),
    "biere": ("l", "produit", ["en:lagers", "en:beers"]),
    "crozets": ("kg", "produit", ["en:crozets"]),
    "quinoa": ("kg", "produit", ["en:quinoa"]),
    "choucroute": ("kg", "produit", ["en:sauerkrauts"]),
    "beaufort": ("kg", "produit", ["en:beaufort"]),
    "reblochon": ("kg", "produit", ["en:reblochon"]),
    "fromage_blanc": ("kg", "produit", ["en:fromage-blanc", "en:fresh-cheeses"]),
    "saindoux": ("kg", "produit", ["en:lards", "en:pork-fats"]),
    "chorizo": ("kg", "produit", ["en:chorizo"]),
    "moules": ("kg", "produit", ["en:mussels"]),
    "canard": ("kg", "produit", ["en:duck-legs", "en:duck-meats"]),
    "lapin": ("kg", "produit", ["en:rabbit-meats", "en:rabbits"]),
    "agneau": ("kg", "produit", ["en:lamb-meats", "en:lamb"]),
    "veau": ("kg", "produit", ["en:veal-meats", "en:veal"]),
    "steak": ("kg", "produit", ["en:beef-steaks", "en:steaks"]),
    "blettes": ("kg", "brut", ["en:chards", "en:swiss-chards"]),
    "pommes": ("kg", "brut", ["en:apples"]),
    "orange": ("piece", "brut", ["en:oranges"]),
    "avocat": ("piece", "brut", ["en:avocados"]),
    "celeri": ("piece", "brut", ["en:celery", "en:celery-stalks"]),
}
ENSEIGNES = [("leclerc", "E.Leclerc"), ("carrefour", "Carrefour"), ("auchan", "Auchan"),
             ("intermarch", "Intermarché"), ("super u", "Système U"), ("hyper u", "Système U"),
             ("u express", "Système U"), ("lidl", "Lidl"), ("aldi", "Aldi"), ("monop", "Monoprix"),
             ("franprix", "Franprix"), ("casino", "Casino"), ("netto", "Netto"),
             ("grand frais", "Grand Frais"), ("biocoop", "Biocoop"), ("picard", "Picard")]
UNITES = {"g": ("kg", 0.001), "kg": ("kg", 1), "ml": ("l", 0.001), "cl": ("l", 0.01), "l": ("l", 1)}


def prix_bas(valeurs):
    """Premier quartile : le prix qu'un foyer attentif à son budget paie
    couramment (la médiane mélange marques premium et premiers prix)."""
    v = sorted(valeurs)
    return statistics.quantiles(v, n=4)[0] if len(v) >= 4 else v[0]


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "EcoCourses/0.1 (github.com/lebenj42)"})
    for essai in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if essai == 2:
                raise
            time.sleep(5)


def enseigne(nom):
    nom = (nom or "").lower()
    return next((e for motif, e in ENSEIGNES if motif in nom), None)


def prix_unitaire(it, unite, genre):
    if it.get("price_is_discounted") or not it.get("price"):
        return None
    prix = float(it["price"])
    if genre == "brut":
        par = it.get("price_per")
        if (unite == "kg" and par == "KILOGRAM") or (unite == "piece" and par == "UNIT"):
            return prix
        return None
    p = it.get("product") or {}
    q, u = p.get("product_quantity"), (p.get("product_quantity_unit") or "g").lower()
    if not q or u not in UNITES or UNITES[u][0] != unite:
        return None
    return prix / (float(q) * UNITES[u][1])


def releves(unite, genre, cat, depuis):
    out = []
    for page in range(1, PAGES + 1):
        p = {"currency": "EUR", "date__gte": depuis, "size": 100, "page": page, "order_by": "-date"}
        p["category_tag" if genre == "brut" else "product__categories_tags__contains"] = cat
        d = get(p)
        for it in d.get("items", []):
            loc = it.get("location") or {}
            if loc.get("osm_address_country") != "France":
                continue
            pu = prix_unitaire(it, unite, genre)
            if pu and 0.05 < pu < 200:
                out.append((pu, enseigne(loc.get("osm_name")), it.get("date")))
        if page >= (d.get("pages") or 1):
            break
        time.sleep(1)
    return out


def main(sortie):
    depuis = (dt.date.today() - dt.timedelta(days=365)).isoformat()
    resultat = {"source": "Open Prices, contributeurs Open Food Facts", "licence": "ODbL 1.0",
                "genere_le": dt.date.today().isoformat(), "depuis": depuis, "ingredients": {}}
    for ing, (unite, genre, cats) in CATEGORIES.items():
        vus = []
        for cat in cats:
            vus = releves(unite, genre, cat, depuis)
            if len(vus) >= 5:
                break
        if not vus:
            print(f"{ing}: aucun relevé exploitable")
            continue
        par_enseigne = defaultdict(list)
        for pu, e, _ in vus:
            if e:
                par_enseigne[e].append(pu)
        resultat["ingredients"][ing] = {
            "unite": unite, "prix": round(prix_bas([p for p, _, _ in vus]), 2), "releves": len(vus),
            "dernier": max((d or "") for _, _, d in vus),
            "enseignes": {e: {"prix": round(prix_bas(v), 2), "releves": len(v)}
                          for e, v in sorted(par_enseigne.items()) if len(v) >= 3},
        }
        r = resultat["ingredients"][ing]
        print(f"{ing}: {r['prix']} €/{unite} sur {r['releves']} relevés, enseignes {r['enseignes']}")
    with open(sortie, "w") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=1)
    print(len(resultat["ingredients"]), "ingrédients couverts sur", len(CATEGORIES))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assets/data/open_prices.json")
