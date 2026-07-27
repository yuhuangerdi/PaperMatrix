from pathlib import Path

from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.repositories.workspace_repository import WorkspaceRepository


def test_workspace_can_be_generated_and_reloaded(tmp_path):
    schema_root = Path(__file__).resolve().parents[2] / "contracts" / "schemas"
    repository = WorkspaceRepository(tmp_path / "workspace", SchemaRegistry(schema_root))

    created = repository.initialize("测试工作区", (tmp_path / "papers",))
    loaded = repository.load()

    assert loaded == created
    assert (repository.root / "projects").is_dir()
    assert (repository.root / ".papermatrix" / "locks").is_dir()
