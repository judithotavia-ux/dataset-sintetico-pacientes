import os
import tempfile
from pathlib import Path

import pytest

# Isola o banco e os arquivos dos testes ANTES de importar a aplicação.
_TMP = Path(tempfile.mkdtemp(prefix="synthetic_tests_"))
os.environ["DATA_DIR"] = str(_TMP)
os.environ.setdefault("LOG_LEVEL", "WARNING")

from fastapi.testclient import TestClient  # noqa: E402

from app import repository  # noqa: E402
from app.config import Settings  # noqa: E402
from app.generator import generate_dataset  # noqa: E402
from app.main import create_app  # noqa: E402

SEED = 123


@pytest.fixture(scope="session")
def dataset():
    """Dataset de 2.000 pacientes, gerado uma vez por sessão de testes."""
    return generate_dataset(2_000, SEED)


@pytest.fixture
def df(dataset):
    """Cópia que cada teste pode alterar livremente."""
    return dataset.copy()


@pytest.fixture
def client(tmp_path):
    repository.clear_cache()
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app) as c:
        yield c
    app.state.db.engine.dispose()
    repository.clear_cache()
