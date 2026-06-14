from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import database


class SoftDeleteAndIsolationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = str(Path(self.temp_dir.name) / "test_shuini.db")
        database.init_db()
        database.create_user("alice", "123456")
        database.create_user("bob", "123456")

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def _create_record(self, *, name: str, username: str, project_id: int, is_admin: bool = False) -> int:
        return database.save_record(
            {
                "name": name,
                "category": "hpc",
                "project_id": project_id,
                "record_data": {"wb": 0.31},
            },
            username=username,
            is_admin=is_admin,
        )

    def test_project_code_uniqueness_is_scoped_per_owner_and_released_after_soft_delete(self) -> None:
        alice_project = database.create_project("PRJ-001", "Alice 项目", "alice")
        bob_project = database.create_project("PRJ-001", "Bob 项目", "bob")

        self.assertNotEqual(alice_project["id"], bob_project["id"])

        database.delete_project(alice_project["id"], username="alice", is_admin=False)
        recreated = database.create_project("PRJ-001", "Alice 新项目", "alice")

        self.assertNotEqual(recreated["id"], alice_project["id"])

    def test_list_queries_are_user_isolated_while_admin_can_view_all(self) -> None:
        alice_project = database.create_project("AL-001", "Alice 项目", "alice")
        bob_project = database.create_project("BO-001", "Bob 项目", "bob")
        alice_record = self._create_record(name="Alice 记录", username="alice", project_id=alice_project["id"])
        self._create_record(name="Bob 记录", username="bob", project_id=bob_project["id"])
        admin_record = self._create_record(
            name="Admin 记录",
            username="admin",
            project_id=alice_project["id"],
            is_admin=True,
        )

        alice_records = database.list_records(username="alice", is_admin=False)["items"]
        self.assertEqual([item["id"] for item in alice_records], [alice_record])

        bob_records = database.list_records(username="bob", is_admin=False)["items"]
        self.assertEqual(len(bob_records), 1)
        self.assertEqual(bob_records[0]["created_by"], "bob")

        admin_records = database.list_records(username="admin", is_admin=True)["items"]
        self.assertEqual({item["id"] for item in admin_records}, {alice_record, admin_record, bob_records[0]["id"]})

        alice_projects = database.list_projects(username="alice", is_admin=False)["items"]
        self.assertEqual(len(alice_projects), 1)
        self.assertEqual(alice_projects[0]["id"], alice_project["id"])
        self.assertEqual(alice_projects[0]["record_count"], 1)

        alice_project_info = database.get_project(alice_project["id"], username="alice", is_admin=False)
        admin_project_info = database.get_project(alice_project["id"], username="admin", is_admin=True)
        self.assertIsNotNone(alice_project_info)
        self.assertIsNotNone(admin_project_info)
        self.assertEqual(alice_project_info["record_count"], 1)
        self.assertEqual(admin_project_info["record_count"], 2)

        alice_project_records = database.list_project_records(alice_project["id"], username="alice", is_admin=False)
        admin_project_records = database.list_project_records(alice_project["id"], username="admin", is_admin=True)
        self.assertEqual([item["id"] for item in alice_project_records], [alice_record])
        self.assertEqual({item["id"] for item in admin_project_records}, {alice_record, admin_record})

        with self.assertRaises(RuntimeError):
            database.list_project_records(bob_project["id"], username="alice", is_admin=False)

    def test_project_soft_delete_cascades_and_restore_keeps_previously_deleted_records_deleted(self) -> None:
        project = database.create_project("AL-010", "Alice 项目", "alice")
        active_record = self._create_record(name="活动记录", username="alice", project_id=project["id"])
        deleted_record = self._create_record(name="先删记录", username="alice", project_id=project["id"])

        database.delete_record(deleted_record, username="alice", is_admin=False)
        database.delete_project(project["id"], username="alice", is_admin=False)

        self.assertIsNone(database.get_project(project["id"], username="alice", is_admin=False))
        self.assertEqual(database.list_records(username="alice", is_admin=False)["items"], [])

        recycle_items = database.list_recycle_bin(username="alice", is_admin=False, page=1, page_size=20)["items"]
        recycle_keys = {(item["item_type"], item["id"]) for item in recycle_items}
        self.assertIn(("project", project["id"]), recycle_keys)
        self.assertIn(("record", active_record), recycle_keys)
        self.assertIn(("record", deleted_record), recycle_keys)

        database.restore_project(project["id"], username="alice", is_admin=False)

        restored_project = database.get_project(project["id"], username="alice", is_admin=False)
        self.assertIsNotNone(restored_project)
        restored_records = database.list_project_records(project["id"], username="alice", is_admin=False)
        self.assertEqual([item["id"] for item in restored_records], [active_record])

        recycle_after_restore = database.list_recycle_bin(username="alice", is_admin=False, page=1, page_size=20)["items"]
        recycle_after_restore_keys = {(item["item_type"], item["id"]) for item in recycle_after_restore}
        self.assertNotIn(("project", project["id"]), recycle_after_restore_keys)
        self.assertIn(("record", deleted_record), recycle_after_restore_keys)

    def test_recycle_bin_supports_record_restore_and_purge(self) -> None:
        project = database.create_project("AL-020", "Alice 项目", "alice")
        record_id = self._create_record(name="待回收记录", username="alice", project_id=project["id"])

        database.delete_record(record_id, username="alice", is_admin=False)
        recycle_items = database.list_recycle_bin(
            username="alice",
            is_admin=False,
            item_type="record",
            page=1,
            page_size=20,
        )["items"]
        self.assertEqual([item["id"] for item in recycle_items], [record_id])

        database.restore_record(record_id, username="alice", is_admin=False)
        active_items = database.list_records(username="alice", is_admin=False)["items"]
        self.assertEqual([item["id"] for item in active_items], [record_id])

        database.delete_record(record_id, username="alice", is_admin=False)
        database.purge_record(record_id, username="alice", is_admin=False)

        conn = database.get_db()
        count = conn.execute("SELECT COUNT(*) FROM records WHERE id=?", (record_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)

    def test_purge_project_removes_project_and_linked_records(self) -> None:
        project = database.create_project("AL-030", "Alice 项目", "alice")
        record_id = self._create_record(name="项目内记录", username="alice", project_id=project["id"])

        database.delete_project(project["id"], username="alice", is_admin=False)
        database.purge_project(project["id"], username="alice", is_admin=False)

        conn = database.get_db()
        project_count = conn.execute("SELECT COUNT(*) FROM projects WHERE id=?", (project["id"],)).fetchone()[0]
        record_count = conn.execute("SELECT COUNT(*) FROM records WHERE id=?", (record_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(project_count, 0)
        self.assertEqual(record_count, 0)


if __name__ == "__main__":
    unittest.main()