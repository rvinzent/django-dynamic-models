import os

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
db_filename = os.environ.get(
    'DYNAMIC_MODELS_DB',
    os.path.join(PROJECT_DIR, 'dynamic_models.db')
)
open(db_filename, 'w').close()
