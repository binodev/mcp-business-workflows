import json
from pathlib import Path

from mcp_business_workflows.schemas.notes import Note


class NoteStore:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]")

    def _load(self) -> list[dict]:  # type: ignore[type-arg]
        return json.loads(self._path.read_text())

    def _save(self, records: list[dict]) -> None:  # type: ignore[type-arg]
        self._path.write_text(json.dumps(records, indent=2, default=str))

    def all(self) -> list[Note]:
        return [Note.model_validate(r) for r in self._load()]

    def insert(self, note: Note) -> None:
        records = self._load()
        records.append(note.model_dump(mode="json"))
        self._save(records)

    def search(self, query: str, tags: list[str]) -> list[Note]:
        q = query.lower()
        results = []
        for note in self.all():
            text_match = q in note.title.lower() or q in note.content.lower()
            tag_match = not tags or any(t in note.tags for t in tags)
            if text_match and tag_match:
                results.append(note)
        return results
