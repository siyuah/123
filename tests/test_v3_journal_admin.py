import json
import tempfile
from pathlib import Path

from tools import journal_admin


def test_journal_backup_restore_and_retention():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        journal = root / "journal.jsonl"
        backup_dir = root / "backups"
        journal.write_text(json.dumps({"eventId": "evt-1"}) + "\n", encoding="utf-8")

        backup_path = journal_admin.backup(journal, backup_dir)
        assert backup_path.exists()
        assert journal_admin.validate_jsonl(backup_path) == 1

        journal.write_text(json.dumps({"eventId": "evt-2"}) + "\n", encoding="utf-8")
        restored_count = journal_admin.restore(backup_path, journal)

        assert restored_count == 1
        assert json.loads(journal.read_text(encoding="utf-8"))["eventId"] == "evt-1"

        removed = journal_admin.retain(backup_dir, keep_last=0, max_age_days=999)
        assert removed == [backup_path]
        assert not backup_path.exists()
