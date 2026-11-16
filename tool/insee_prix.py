"""Télécharge les prix moyens de vente au détail de l'Insee (jeu DS_IPC_PM)
et écrit le dernier prix connu de chaque produit alimentaire.

Usage : python3 tool/insee_prix.py [sortie.json]
Source : https://www.data.gouv.fr/datasets/prix-moyens-de-vente-de-detail
(Licence Ouverte Etalab). Le fichier n'est pas joignable depuis tous les
environnements : la CI GitHub y a accès.
"""
import csv
import io
import json
import sys
import urllib.request
import zipfile

URL = "https://api.insee.fr/melodi/file/DS_IPC_PM/DS_IPC_PM_CSV_FR"
NON_ALIMENTAIRE = ("Services", "Fleurs", "Boissons alcoolisées", "Tabac", "Non alimentaire",
                   "Essence", "Gazole", "Fioul", "Supercarburant")


def lire_zip(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    noms = z.namelist()
    meta = next(n for n in noms if "metadata" in n)
    donnees = next(n for n in noms if "data" in n and n != meta)
    return (z.read(meta).decode("utf-8-sig"), z.read(donnees).decode("utf-8-sig"))


def libelles(meta_csv):
    out = {}
    for row in csv.DictReader(io.StringIO(meta_csv), delimiter=";"):
        if row["COD_VAR"] == "PRODUCT_ITEM":
            out[row["COD_MOD"]] = row["LIB_MOD"]
    return out


def derniers_prix(data_csv):
    """Dernière observation mensuelle normale par produit (annuelle à défaut)."""
    best = {}
    for row in csv.DictReader(io.StringIO(data_csv), delimiter=";"):
        if row["OBS_STATUS"] != "A" or not row["OBS_VALUE"]:
            continue
        code, freq, periode = row["PRODUCT_ITEM"], row["FREQ"], row["TIME_PERIOD"]
        cle = (1 if freq == "M" else 0, periode)
        if code not in best or cle > best[code][0]:
            best[code] = (cle, periode, float(row["OBS_VALUE"]))
    return {code: (p, v) for code, (_, p, v) in best.items()}


def main():
    sortie = sys.argv[1] if len(sys.argv) > 1 else "insee_prix_moyens.json"
    with urllib.request.urlopen(URL, timeout=120) as r:
        meta_csv, data_csv = lire_zip(r.read())
    noms = libelles(meta_csv)
    prix = derniers_prix(data_csv)
    lignes = []
    for code, (periode, valeur) in sorted(prix.items(), key=lambda x: noms.get(x[0], "")):
        nom = noms.get(code, code)
        if nom.startswith(NON_ALIMENTAIRE):
            continue
        lignes.append({"code": code, "libelle": nom, "prix": valeur, "periode": periode})
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(lignes, f, ensure_ascii=False, indent=1)
    for l in lignes:
        print(f'{l["code"]}\t{l["periode"]}\t{l["prix"]}\t{l["libelle"]}')
    print(len(lignes), "produits écrits dans", sortie)


if __name__ == "__main__":
    main()
