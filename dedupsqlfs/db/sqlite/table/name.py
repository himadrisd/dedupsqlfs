# -*- coding: utf8 -*-

__author__ = 'sergey'

import hashlib
import sqlite3
from dedupsqlfs.db.sqlite.table import Table

class TableName( Table ):

    _table_name = "name"

    def create(self):
        c = self.getCursor()

        # Create table
        c.execute(
            "CREATE TABLE IF NOT EXISTS `%s` (" % self._table_name+
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "+
                "hash BINARY(16) NOT NULL, "+
                "value BLOB NOT NULL "+
            ");"
        )
        self.createIndexIfNotExists('hash', ('hash',), True)
        return

    def getRowSize(self, value):
        """
        :param value: bytes
        :return: int
        """
        bvalue = sqlite3.Binary(value)
        return 8 + 16 + len(bvalue)*2

    def insert(self, value):
        """
        :param value: bytes
        :return: int
        """
        self.startTimer()
        cur = self.getCursor()

        digest = sqlite3.Binary(hashlib.new('md5', value).digest())

        bvalue = sqlite3.Binary(value)

        cur.execute("INSERT INTO `%s`(hash,value) VALUES (?,?)" % self.getName(), (digest,bvalue,))
        item = cur.lastrowid
        self.stopTimer('insert')
        return item

    def insertRaw(self, rowId, value):
        """
        :param value: bytes
        :return: int
        """
        self.startTimer()
        cur = self.getCursor()

        digest = sqlite3.Binary(hashlib.new('md5', value).digest())

        bvalue = sqlite3.Binary(value)

        cur.execute("INSERT INTO `%s`(id,hash,value) VALUES (?,?,?)" % self.getName(), (rowId, digest, bvalue,))
        item = cur.lastrowid
        self.stopTimer('insertRaw')
        return item

    def find(self, value):
        """
        :param value: bytes
        :return: int
        """
        self.startTimer()
        cur = self.getCursor()

        digest = sqlite3.Binary(hashlib.new('md5', value).digest())

        cur.execute("SELECT id FROM `%s` WHERE hash=?" % self._table_name, (digest,))
        item = cur.fetchone()
        if item:
            item = item["id"]
        self.stopTimer('find')
        return item

    def get(self, name_id):
        """
        :param name_id: int
        :return: bytes
        """
        self.startTimer()
        cur = self.getCursor()

        cur.execute("SELECT value FROM `%s` WHERE id=?" % self._table_name, (name_id,))
        item = cur.fetchone()
        if item:
            item = item["value"]
        self.stopTimer('get')
        return item

    def get_count(self):
        self.startTimer()
        cur = self.getCursor()
        cur.execute("SELECT COUNT(1) as `cnt` FROM `%s`" % self.getName())
        item = cur.fetchone()
        if item:
            item = item["cnt"]
        else:
            item = 0
        self.stopTimer('get_count')
        return item

    def get_name_ids(self, start_id, end_id):
        self.startTimer()
        cur = self.getCursor()
        cur.execute("SELECT `id` FROM `%s` " % self.getName()+
                    " WHERE `id`>=? AND `id`<?", (start_id, end_id,))
        nameIds = set(item["id"] for item in iter(cur.fetchone, None))
        self.stopTimer('get_name_ids')
        return nameIds

    def remove_by_ids(self, id_str):
        self.startTimer()
        count = 0
        if id_str:
            cur = self.getCursor()
            cur.execute("DELETE FROM `%s` WHERE `id` IN (%s)" % (self.getName(), id_str,))
            count = cur.rowcount
        self.stopTimer('remove_by_ids')
        return count

    pass
