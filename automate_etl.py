import subprocess
import os
import sys
from datetime import datetime

def create_log_file():
    """Crée le dossier logs et un fichier log unique"""
    os.makedirs("logs", exist_ok=True)
    return f"logs/automate_etl_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

def log_message(f, message, level="INFO"):
    """Écrit un message dans le log avec timestamp et niveau"""
    f.write(f"[{level}] {datetime.now()} - {message}\n")

def run_script(script_name, log_file):

    """
    Exécute un script Python et écrit stdout + stderr dans le fichier log.
    Permet de suivre étape par étape l'exécution du pipeline.
    """
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            log_message(f, f"Début de l'exécution de {script_name}")
            
            result = subprocess.run(
                [sys.executable, script_name],
                stdout=f,            # Redirige la sortie standard vers le log
                stderr=f,             # Redirige les erreurs vers le log
                text=True
            )
            
            if result.returncode != 0:
                log_message(f, f"{script_name} a échoué avec le code {result.returncode}", level="ERROR")
            else:
                log_message(f, f"{script_name} terminé avec succès ")
    except Exception as e:
        with open(log_file, "a", encoding="utf-8") as f:
            log_message(f, f"Erreur inattendue lors de l'exécution de {script_name}: {e}", level="ERROR")

if __name__ == "__main__":
    log_file = create_log_file()
    print(f"Pipeline ETL démarré à {datetime.now()}")
    
    # Liste des scripts à exécuter dans l'ordre
    scripts = ["main.py", "clean_products.py", "load_to_postgres.py"]
    
    # # Boucle sur chaque script pour l'exécuter et loguer son résultat
    for script in scripts:
        run_script(script, log_file)
    
    print(f"Pipeline ETL terminé à {datetime.now()}")
    print(f"Voir le log complet dans : {log_file}")

