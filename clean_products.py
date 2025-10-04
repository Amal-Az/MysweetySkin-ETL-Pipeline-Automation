"""
clean_products.py
Nettoyage des données extraites depuis raw_products.csv
"""

import pandas as pd
import os
from datetime import datetime

RAW_FILE = "data/raw_products.csv"
CLEAN_FILE = "data/clean_products.csv"

def clean_data():
    if not os.path.exists(RAW_FILE):
        print(f" Fichier introuvable: {RAW_FILE}")
        return
    
    # Charger la data
    df = pd.read_csv(RAW_FILE)

    print(f"Données brutes: {df.shape[0]} lignes, {df.shape[1]} colonnes")
    # print(df.head(15))

    # Supprimer la colonne inutile "price_text"
    if "price_text" in df.columns:
        df.drop(columns=["price_text"], inplace=True)

    # Supprimer les doublons dans la même collection
    before = df.shape[0]
    df.drop_duplicates(subset=["title", "collection"], inplace=True)
    after = df.shape[0]
    print(f" Doublons supprimés: {before - after}")

    # Vérifier les lignes avec price_value vide
    missing_price = df[df["price_value"].isna()]
    if not missing_price.empty:
        print(f" {len(missing_price)} lignes avec prix manquant :")
        print(missing_price[["title", "collection", "link"]].head(10))

    #  Supprimer les lignes où availability = "Inconnu"
    before = df.shape[0]
    df = df[df["availability"] != "Inconnu"]
    after = df.shape[0]
    print(f" Produits supprimés car 'Inconnu': {before - after}")

    # Ajouter une colonne date_scraped
    df["date_scraped"] = datetime.now()


    # Sauvegarde
    os.makedirs("data", exist_ok=True)
    df.to_csv(CLEAN_FILE, index=False, encoding="utf-8-sig")

    print(f" Nettoyage terminé. {df.shape[0]} produits sauvegardés dans {CLEAN_FILE}")


if __name__ == "__main__":
    clean_data()
