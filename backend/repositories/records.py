"""Compatibility wrappers for record persistence.

The authoritative record storage implementation now lives in database.py.
Keep this module as a thin re-export so older imports do not drift onto a
stale schema definition.
"""

from database import delete_record, list_project_records, list_records, save_record

__all__ = ["save_record", "list_records", "delete_record", "list_project_records"]