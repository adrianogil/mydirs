import os
import sqlite3


SCHEMA_VERSION = 2
IDENTITY_BACKFILL_KEY = 'filesystem_identity_backfill_v2'


class MyDirsDao:
    """SQLite persistence for aliases and their navigation metadata."""

    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file, timeout=5)
        self.conn.execute('PRAGMA busy_timeout = 5000')
        self.c = self.conn.cursor()
        self._migrate()

    def _migrate(self):
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            current_version = self.c.execute(
                'PRAGMA user_version'
            ).fetchone()[0]
            if current_version > SCHEMA_VERSION:
                raise ValueError(
                    'database schema version %d is newer than supported '
                    'version %d' % (current_version, SCHEMA_VERSION)
                )
            self.c.execute('''
                CREATE TABLE IF NOT EXISTS PathByKey (
                    id_pathbykey INTEGER,
                    path TEXT,
                    path_key TEXT NOT NULL COLLATE BINARY,
                    PRIMARY KEY (id_pathbykey)
                )
            ''')

            columns = {
                row[1] for row in self.c.execute('PRAGMA table_info(PathByKey)')
            }
            migrations = (
                ('usage_count', 'INTEGER NOT NULL DEFAULT 0'),
                ('last_used_at', 'INTEGER'),
                ('device_id', 'TEXT'),
                ('inode', 'TEXT'),
            )
            for column, definition in migrations:
                if column not in columns:
                    self.c.execute(
                        'ALTER TABLE PathByKey ADD COLUMN %s %s'
                        % (column, definition)
                    )

            self.c.execute('''
                CREATE TABLE IF NOT EXISTS MyDirsMetadata (
                    key TEXT PRIMARY KEY COLLATE BINARY,
                    value TEXT NOT NULL
                )
            ''')
            self.c.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_pathbykey_path_key
                ON PathByKey(path_key COLLATE BINARY)
            ''')
            self.c.execute('PRAGMA user_version = %d' % SCHEMA_VERSION)
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        self._backfill_filesystem_identity_once()

    @staticmethod
    def filesystem_identity(path):
        try:
            stat_result = os.stat(path)
        except OSError:
            return None, None
        # Decimal text avoids overflowing SQLite's signed 64-bit INTEGER on
        # filesystems whose POSIX identity values are unsigned 64-bit.
        return str(stat_result.st_dev), str(stat_result.st_ino)

    def _backfill_filesystem_identity_once(self):
        self.conn.execute('BEGIN IMMEDIATE')
        if self.conn.execute(
            'SELECT 1 FROM MyDirsMetadata WHERE key = ?',
            (IDENTITY_BACKFILL_KEY,),
        ).fetchone() is not None:
            self.conn.commit()
            return
        rows = self.c.execute('''
            SELECT id_pathbykey, path
            FROM PathByKey
            WHERE device_id IS NULL OR inode IS NULL
        ''').fetchall()
        updates = []
        for row_id, path in rows:
            device_id, inode = self.filesystem_identity(path)
            if device_id is not None:
                updates.append((device_id, inode, row_id))
        try:
            if updates:
                self.conn.executemany('''
                    UPDATE PathByKey
                    SET device_id = ?, inode = ?
                    WHERE id_pathbykey = ?
                ''', updates)
            self.conn.execute(
                'INSERT INTO MyDirsMetadata(key, value) VALUES (?, ?)',
                (IDENTITY_BACKFILL_KEY, '1'),
            )
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def get_metadata(self, key):
        row = self.conn.execute(
            'SELECT value FROM MyDirsMetadata WHERE key = ?', (key,)
        ).fetchone()
        return None if row is None else row[0]

    def set_metadata(self, key, value):
        with self.conn:
            self.conn.execute('''
                INSERT OR REPLACE INTO MyDirsMetadata(key, value) VALUES (?, ?)
            ''', (key, str(value)))

    def add_alias(self, path_key, path):
        device_id, inode = self.filesystem_identity(path)
        with self.conn:
            self.conn.execute('''
                INSERT INTO PathByKey (
                    path, path_key, usage_count, last_used_at, device_id, inode
                ) VALUES (?, ?, 0, NULL, ?, ?)
            ''', (path, path_key, device_id, inode))

    def replace_alias(self, path_key, path, preserve_usage=True):
        device_id, inode = self.filesystem_identity(path)
        with self.conn:
            if preserve_usage:
                cursor = self.conn.execute('''
                    UPDATE PathByKey
                    SET path = ?, device_id = ?, inode = ?
                    WHERE path_key = ? COLLATE BINARY
                ''', (path, device_id, inode, path_key))
                if cursor.rowcount:
                    return
            self.conn.execute(
                'DELETE FROM PathByKey WHERE path_key = ? COLLATE BINARY',
                (path_key,),
            )
            self.conn.execute('''
                INSERT INTO PathByKey (
                    path, path_key, usage_count, last_used_at, device_id, inode
                ) VALUES (?, ?, 0, NULL, ?, ?)
            ''', (path, path_key, device_id, inode))

    def remove_alias(self, path_key):
        with self.conn:
            self.conn.execute(
                'DELETE FROM PathByKey WHERE path_key = ? COLLATE BINARY',
                (path_key,),
            )

    def alias(self, path_key):
        return self.conn.execute('''
            SELECT id_pathbykey, path, path_key, usage_count, last_used_at,
                   device_id, inode
            FROM PathByKey
            WHERE path_key = ? COLLATE BINARY
        ''', (path_key,)).fetchone()

    def aliases(self):
        return self.conn.execute('''
            SELECT id_pathbykey, path, path_key, usage_count, last_used_at,
                   device_id, inode
            FROM PathByKey
        ''').fetchall()

    def record_use(self, path_key, used_at):
        """Increment usage atomically so concurrent shells cannot lose counts."""
        with self.conn:
            cursor = self.conn.execute('''
            UPDATE PathByKey
                SET usage_count = usage_count + 1,
                    last_used_at = CASE
                        WHEN last_used_at IS NULL OR last_used_at < ? THEN ?
                        ELSE last_used_at
                    END
                WHERE path_key = ? COLLATE BINARY
            ''', (int(used_at), int(used_at), path_key))
        return cursor.rowcount == 1

    def import_legacy_path_counts_once(self, migration_key, counts):
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            if self.conn.execute(
                'SELECT 1 FROM MyDirsMetadata WHERE key = ?',
                (migration_key,),
            ).fetchone() is not None:
                self.conn.commit()
                return False
            for path, count in counts.items():
                self.conn.execute('''
                    UPDATE PathByKey
                    SET usage_count = usage_count + ?
                    WHERE path = ?
                ''', (count, path))
            self.conn.execute(
                'INSERT INTO MyDirsMetadata(key, value) VALUES (?, ?)',
                (migration_key, '1'),
            )
            self.conn.commit()
            return True
        except BaseException:
            self.conn.rollback()
            raise

    def close(self):
        self.c.close()
        self.conn.close()
