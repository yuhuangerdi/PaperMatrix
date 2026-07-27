from fastapi.testclient import TestClient

from papermatrix.core.config import Settings
from papermatrix.main import create_app


def test_health_reports_uninitialized_workspace(tmp_path):
    app = create_app(
        Settings(workspace_root=tmp_path),
        schema_root=__import__("pathlib").Path(__file__).resolve().parents[2]
        / "contracts"
        / "schemas",
    )

    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "workspace_initialized": False,
    }
    assert response.headers["X-Request-ID"]
