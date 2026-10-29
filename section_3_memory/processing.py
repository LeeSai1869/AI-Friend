"""Durable post-intake queue with append-only processing history.

This database records operational metadata, not mutable Raw content. A lease
serializes intake examination across sessions without holding a database
transaction while a domain works.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
import uuid


class ProcessingJournal:
    def __init__(self, root):
        self.path = Path(root) / 'intake_processing.sqlite3'
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS sources (
                    raw_id TEXT PRIMARY KEY, domain TEXT NOT NULL,
                    content_hash TEXT NOT NULL, created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, raw_id TEXT NOT NULL,
                    created_at REAL NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS source_events ON events(raw_id, id);
                CREATE TABLE IF NOT EXISTS worker_lease (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), token TEXT, expires REAL
                );
            ''')

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _event(db, raw_id, state, payload):
        db.execute('INSERT INTO events(raw_id,created_at,state,payload) VALUES(?,?,?,?)',
                   (raw_id, time.time(), state, json.dumps(payload, ensure_ascii=False, allow_nan=False)))

    def enqueue(self, raw_id, domain, digest):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?)',
                                 (raw_id, domain, digest, time.time())).rowcount
            if changed:
                self._event(db, raw_id, 'queued', {'storage':'stored','processing':'queued',
                            'verification':'not_attempted','decision':'pending'})
        return self.status(raw_id)

    def status(self, raw_id):
        with self.connect() as db:
            source = db.execute('SELECT * FROM sources WHERE raw_id=?', (raw_id,)).fetchone()
            if source is None:
                return None
            event = db.execute('SELECT * FROM events WHERE raw_id=? ORDER BY id DESC LIMIT 1', (raw_id,)).fetchone()
            return {**dict(source), **json.loads(event['payload']), 'state':event['state'], 'updated_at':event['created_at']}

    def history(self, raw_id):
        with self.connect() as db:
            return [{'event_id':row['id'],'state':row['state'],'created_at':row['created_at'],
                     **json.loads(row['payload'])} for row in db.execute('SELECT * FROM events WHERE raw_id=? ORDER BY id', (raw_id,))]

    def list(self, limit=50):
        with self.connect() as db:
            ids = [row[0] for row in db.execute('SELECT raw_id FROM sources ORDER BY created_at DESC LIMIT ?', (max(1,min(limit,200)),))]
        return [self.status(raw_id) for raw_id in ids]

    def pending(self, limit=4):
        with self.connect() as db:
            return [row[0] for row in db.execute(
                "SELECT s.raw_id FROM sources s JOIN events e ON e.id=(SELECT MAX(id) FROM events WHERE raw_id=s.raw_id) "
                "WHERE e.state IN ('queued','examining') ORDER BY s.created_at LIMIT ?", (max(1,min(limit,16)),))]

    def claim(self, raw_id, *, retry=False, seconds=900):
        token = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM sources WHERE raw_id=?',(raw_id,)).fetchone() is None:
                raise ValueError('Raw source is not queued')
            lease = db.execute('SELECT * FROM worker_lease WHERE singleton=1').fetchone()
            if lease and lease['token'] and lease['expires'] > time.time():
                return None
            latest = db.execute('SELECT state FROM events WHERE raw_id=? ORDER BY id DESC LIMIT 1',(raw_id,)).fetchone()[0]
            if latest not in {'queued','processing_failed','examining'} and not retry:
                return None
            if latest == 'examining':
                self._event(db,raw_id,'processing_failed',{'storage':'stored','processing':'failed',
                            'verification':'not_attempted','decision':'pending','reason':'Previous processing attempt was interrupted'})
            db.execute('INSERT OR REPLACE INTO worker_lease VALUES(1,?,?)',(token,time.time()+seconds))
            self._event(db,raw_id,'examining',{'storage':'stored','processing':'examining','verification':'not_attempted','decision':'pending'})
        return token

    def finish(self, raw_id, token, *, state, payload):
        if state not in {'completed','deferred','processing_failed'}:
            raise ValueError('invalid processing outcome')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            lease = db.execute('SELECT token FROM worker_lease WHERE singleton=1').fetchone()
            if lease is None or lease['token'] != token:
                raise RuntimeError('Processing lease was lost; result was not recorded')
            self._event(db, raw_id, state, {'storage':'stored', **payload})
            db.execute('UPDATE worker_lease SET token=NULL,expires=0 WHERE singleton=1')
        return self.status(raw_id)
