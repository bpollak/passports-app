import os
import unittest
from unittest.mock import patch

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base
from backend.models import Location
from backend.seed import get_configured_password_hashes, seed_database


def _test_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=4)
    ).decode("utf-8")


def _configured_hashes(csc_hash: str, bookstore_hash: str) -> dict[str, str]:
    return {
        "LOCATION_CSC_PASSWORD_HASH": csc_hash,
        "LOCATION_BOOKSTORE_PASSWORD_HASH": bookstore_hash,
    }


class ConfiguredPasswordHashTests(unittest.TestCase):
    def test_all_location_hashes_are_required(self):
        csc_hash = _test_hash("configured-csc-password")

        with patch.dict(
            os.environ,
            {"LOCATION_CSC_PASSWORD_HASH": csc_hash},
            clear=True,
        ):
            with self.assertRaises(RuntimeError) as raised:
                get_configured_password_hashes()

        message = str(raised.exception)
        self.assertIn("LOCATION_BOOKSTORE_PASSWORD_HASH", message)
        self.assertNotIn(csc_hash, message)

    def test_location_hashes_must_be_distinct(self):
        shared_hash = _test_hash("shared-location-password")

        with patch.dict(
            os.environ,
            _configured_hashes(shared_hash, shared_hash),
            clear=True,
        ):
            with self.assertRaises(RuntimeError) as raised:
                get_configured_password_hashes()

        message = str(raised.exception)
        self.assertIn("LOCATION_CSC_PASSWORD_HASH", message)
        self.assertIn("LOCATION_BOOKSTORE_PASSWORD_HASH", message)
        self.assertNotIn(shared_hash, message)

    def test_location_hashes_must_be_valid_bcrypt(self):
        csc_hash = _test_hash("configured-csc-password")

        with patch.dict(
            os.environ,
            _configured_hashes(csc_hash, "not-a-bcrypt-hash"),
            clear=True,
        ):
            with self.assertRaises(RuntimeError) as raised:
                get_configured_password_hashes()

        self.assertIn("LOCATION_BOOKSTORE_PASSWORD_HASH", str(raised.exception))


class SeedDatabasePasswordHashTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessionmaker = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _insert_locations(self, csc_hash: str, bookstore_hash: str):
        async with self.sessionmaker() as db:
            db.add_all(
                [
                    Location(
                        id="csc",
                        name="CSC",
                        password_hash=csc_hash,
                    ),
                    Location(
                        id="bookstore",
                        name="Bookstore",
                        password_hash=bookstore_hash,
                    ),
                ]
            )
            await db.commit()

    async def test_empty_database_bootstraps_configured_hashes(self):
        csc_hash = _test_hash("configured-csc-password")
        bookstore_hash = _test_hash("configured-bookstore-password")

        with patch.dict(
            os.environ,
            _configured_hashes(csc_hash, bookstore_hash),
            clear=True,
        ):
            async with self.sessionmaker() as db:
                returned_hashes = await seed_database(db)
                rows = (
                    await db.execute(select(Location).order_by(Location.id))
                ).scalars().all()

        self.assertEqual(
            returned_hashes,
            {"csc": csc_hash, "bookstore": bookstore_hash},
        )
        self.assertEqual(
            [(row.id, row.password_hash) for row in rows],
            [("bookstore", bookstore_hash), ("csc", csc_hash)],
        )

    async def test_configured_hash_overwrites_stale_database_hash(self):
        stale_csc_hash = _test_hash("stale-csc-password")
        configured_csc_hash = _test_hash("configured-csc-password")
        bookstore_hash = _test_hash("configured-bookstore-password")
        await self._insert_locations(stale_csc_hash, bookstore_hash)

        with patch.dict(
            os.environ,
            _configured_hashes(configured_csc_hash, bookstore_hash),
            clear=True,
        ):
            async with self.sessionmaker() as db:
                returned_hashes = await seed_database(db)
                rows = (
                    await db.execute(select(Location).order_by(Location.id))
                ).scalars().all()

        self.assertEqual(
            returned_hashes,
            {"csc": configured_csc_hash, "bookstore": bookstore_hash},
        )
        self.assertEqual(
            [(row.id, row.password_hash) for row in rows],
            [("bookstore", bookstore_hash), ("csc", configured_csc_hash)],
        )
        self.assertNotIn(stale_csc_hash, [row.password_hash for row in rows])


if __name__ == "__main__":
    unittest.main()
