"""records JSON 快照字段持久化回归测试。"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import database


class RecordTrialDataPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = str(Path(self.temp_dir.name) / "test_shuini.db")
        database.init_db()
        self.project = database.create_project("P-001", "试配项目", "admin")

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_records_table_uses_metadata_plus_json_payload_storage(self) -> None:
        conn = database.get_db()
        columns = [row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()]
        conn.close()

        self.assertEqual(
            columns,
            [
                "id",
                "name",
                "category",
                "created_by",
                "created_at",
                "project_id",
                "record_data",
                "is_deleted",
                "deleted_at",
                "deleted_by",
                "deleted_with_project",
            ],
        )

    def test_trial_data_round_trip_and_partial_update_preserves_snapshot(self) -> None:
        trial_snapshot = {
            "version": 1,
            "inputs": {
                "batchVolume": 20,
                "workabilityBinderDelta": 10,
                "deltaWb": 0.02,
                "sTargetStrength": 68,
            },
            "calculated": {
                "baseWb": 0.31,
                "baseBs": 41,
                "baseAlpha": 1.5,
            },
        }

        record_id = database.save_record({
            "name": "高性能配比",
            "category": "hpc",
            "project_id": self.project["id"],
            "record_data": {
                "wb": 0.31,
                "mb": 520,
                "trial_data": trial_snapshot,
            },
        }, username="admin", is_admin=True)

        created_items = database.list_records(
            project_id=self.project["id"],
            username="admin",
            is_admin=True,
        )["items"]

        self.assertEqual(len(created_items), 1)
        self.assertEqual(created_items[0]["id"], record_id)
        self.assertEqual(created_items[0]["record_data"]["trial_data"], trial_snapshot)

        database.save_record({
            "id": record_id,
            "name": "高性能配比-更新",
            "category": "hpc",
            "project_id": self.project["id"],
            "record_data": {"wb": 0.305},
        }, username="admin", is_admin=True)

        updated_items = database.list_records(
            project_id=self.project["id"],
            username="admin",
            is_admin=True,
        )["items"]

        self.assertEqual(len(updated_items), 1)
        self.assertEqual(updated_items[0]["name"], "高性能配比-更新")
        self.assertEqual(updated_items[0]["record_data"]["wb"], 0.305)
        self.assertEqual(updated_items[0]["record_data"]["trial_data"], trial_snapshot)

        conn = database.get_db()
        payload_text = conn.execute(
            "SELECT record_data FROM records WHERE id=?",
            (record_id,),
        ).fetchone()[0]
        conn.close()
        payload = json.loads(payload_text)
        self.assertEqual(payload["wb"], 0.305)
        self.assertEqual(payload["trial_data"], trial_snapshot)

    def test_design_data_round_trip_and_partial_update_preserves_snapshot(self) -> None:
        design_snapshot = {
            "version": 1,
            "inputs": {
                "strengthGrade": 130,
                "waterBinderRatio": 0.19,
                "sandBinderRatio": 1.2,
            },
            "calculated": {
                "designStrength": 143.0,
                "materialMasses": {
                    "binder": 782.44,
                    "total": 2500.0,
                },
            },
        }

        record_id = database.save_record({
            "name": "UHPC 配比",
            "category": "uhpc",
            "project_id": self.project["id"],
            "record_data": {
                "wb": 0.19,
                "mb": 782.44,
                "design_data": design_snapshot,
            },
        }, username="admin", is_admin=True)

        created_items = database.list_records(
            project_id=self.project["id"],
            username="admin",
            is_admin=True,
        )["items"]

        self.assertEqual(len(created_items), 1)
        self.assertEqual(created_items[0]["id"], record_id)
        self.assertEqual(created_items[0]["record_data"]["design_data"], design_snapshot)

        database.save_record({
            "id": record_id,
            "name": "UHPC 配比-更新",
            "category": "uhpc",
            "project_id": self.project["id"],
            "record_data": {"wb": 0.185},
        }, username="admin", is_admin=True)

        updated_items = database.list_records(
            project_id=self.project["id"],
            username="admin",
            is_admin=True,
        )["items"]

        self.assertEqual(len(updated_items), 1)
        self.assertEqual(updated_items[0]["name"], "UHPC 配比-更新")
        self.assertEqual(updated_items[0]["record_data"]["wb"], 0.185)
        self.assertEqual(updated_items[0]["record_data"]["design_data"], design_snapshot)

        conn = database.get_db()
        payload_text = conn.execute(
            "SELECT record_data FROM records WHERE id=?",
            (record_id,),
        ).fetchone()[0]
        conn.close()
        payload = json.loads(payload_text)
        self.assertEqual(payload["wb"], 0.185)
        self.assertEqual(payload["design_data"], design_snapshot)

    def test_init_db_backfills_legacy_record_columns_into_record_data(self) -> None:
        legacy_db_path = Path(self.temp_dir.name) / "legacy_records.db"
        database.DB_PATH = str(legacy_db_path)

        conn = sqlite3.connect(database.DB_PATH)
        conn.executescript(
            """
            CREATE TABLE records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                wb REAL,
                mb REAL,
                trial_data TEXT,
                design_data TEXT
            );
            """
        )
        trial_snapshot = {"version": 1, "inputs": {"deltaWb": 0.02}}
        design_snapshot = {"version": 1, "inputs": {"strengthGrade": 150}}
        conn.execute(
            "INSERT INTO records (name, created_by, wb, mb, trial_data, design_data) VALUES (?,?,?,?,?,?)",
            (
                "旧版配比",
                "admin",
                0.31,
                520.0,
                json.dumps(trial_snapshot, ensure_ascii=False),
                json.dumps(design_snapshot, ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()

        database.init_db()

        migrated_items = database.list_records(username="admin", is_admin=True)["items"]
        self.assertEqual(len(migrated_items), 1)
        self.assertEqual(migrated_items[0]["category"], "hpc")
        self.assertEqual(migrated_items[0]["record_data"]["wb"], 0.31)
        self.assertEqual(migrated_items[0]["record_data"]["mb"], 520.0)
        self.assertEqual(migrated_items[0]["record_data"]["trial_data"], trial_snapshot)
        self.assertEqual(migrated_items[0]["record_data"]["design_data"], design_snapshot)

        conn = database.get_db()
        payload_text = conn.execute("SELECT record_data FROM records WHERE id=1").fetchone()[0]
        conn.close()
        payload = json.loads(payload_text)
        self.assertEqual(payload["wb"], 0.31)
        self.assertEqual(payload["mb"], 520.0)
        self.assertEqual(payload["trial_data"], trial_snapshot)
        self.assertEqual(payload["design_data"], design_snapshot)


if __name__ == "__main__":
    unittest.main()