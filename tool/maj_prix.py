"""Met à jour les prix de ingredients.json avec les derniers relevés.

Reprend la règle de l'appli Eco Courses : prix Open Prices (premier quartile
des relevés en rayon, par ingrédient et par enseigne) quand il y a au moins
MIN_RELEVES relevés, sinon prix moyen Insee quand le produit y figure, sinon
le prix déjà publié. Les noms, rayons et conditionnements ne changent pas.

Usage : python3 tool/maj_prix.py OPEN_PRICES.json INSEE.json ingredients.json
"""
import json
import pathlib
import sys

# Ingrédient -> (code Insee, facteur) : prix Insee x facteur = prix dans l'unité de l'ingrédient.
INSEE = {
  "carottes": ("8948", 1), "champignons": ("8949", 1), "chou_fleur": ("3838", 1),
  "courgettes": ("8951", 1), "oignons": ("8953", 1), "poireaux": ("8954", 1),
  "poivrons": ("3965", 1), "pdt": ("8959", 1), "tomates": ("8955", 1),
  "citron": ("8934", 0.13),  # un citron pèse environ 130 g
  "porc_echine": ("1266", 1), "jambon": ("1272", 1),
}

# Nombre minimal de relevés Open Prices pour préférer ce prix à l'Insee.
MIN_RELEVES = 8


def lire(chemin, defaut):
    p = pathlib.Path(chemin)
    return json.loads(p.read_text()) if p.exists() else defaut


def main(op_path, insee_path, ing_path):
    open_prices = lire(op_path, {}).get("ingredients", {})
    insee = {r["code"]: r for r in lire(insee_path, [])}
    ingredients = json.loads(pathlib.Path(ing_path).read_text())
    changes = 0
    for ing in ingredients:
        avant = (ing["prix"], ing.get("enseignes"))
        if ing["id"] in INSEE and INSEE[ing["id"]][0] in insee and ing.get("source") != "open_prices":
            code, facteur = INSEE[ing["id"]]
            ing["prix"] = round(insee[code]["prix"] * facteur, 2)
            ing["source"] = "insee"
            ing["date"] = insee[code]["periode"]
        op = open_prices.get(ing["id"])
        if op and op["unite"] == ing["unite"] and op["releves"] >= MIN_RELEVES:
            ing["prix"] = op["prix"]
            ing["source"] = "open_prices"
            ing["date"] = op["dernier"][:7]
            ing["enseignes"] = {e: v["prix"] for e, v in op["enseignes"].items()}
        changes += avant != (ing["prix"], ing.get("enseignes"))
    pathlib.Path(ing_path).write_text(json.dumps(ingredients, ensure_ascii=False, indent=1))
    print(changes, "prix modifiés sur", len(ingredients))


if __name__ == "__main__":
    main(*sys.argv[1:4])
