import pandas as pd
from sqlalchemy import create_engine

# -----------------------------
# CONFIGURATION DE LA CONNEXION
# -----------------------------

DB_USER = "postgres"
DB_PASSWORD = "amal"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "myskin_db"

# Connexion via SQLAlchemy
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


# CHARGEMENT DU CSV
file_path = "data/clean_products.csv"  
df = pd.read_csv(file_path)

print(f" Données à insérer : {len(df)} lignes, {len(df.columns)} colonnes")


# INSERTION DANS LA TABLE
df.to_sql("products", engine, if_exists="append", index=False)

print(" Insertion terminée ! Les données sont maintenant dans PostgreSQL.")
