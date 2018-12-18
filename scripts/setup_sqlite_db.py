import os

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
db_file = os.environ.get(
    'DYNAMIC_MODELS_DB',
    os.path.join(PROJECT_DIR, 'dynamic_models.db')
)
open(db_file, 'w').close()
