# -*- coding: utf8 -*-

__author__ = 'sergey'

from time import time
import os
import sys
import subprocess

from dedupsqlfs.db.sqlite.row import dict_factory
from dedupsqlfs.log import logging
from dedupsqlfs.my_formats import format_size

class Table( object ):

    _conn = None
    _curr = None

    _db_file_path = None
    _table_name = None
    _manager = None
    _autocommit = True

    _last_time = None
    _time_spent = None
    _op_count = None

    _log = None

    # default start page size for SQLite db file
    _page_size = 512

    def __init__(self, manager):
        if self._table_name is None:
            raise AttributeError("Define non-empty class variable '_table_name'")
        self._manager = manager
        self._time_spent = {}
        self._op_count = {}
        pass

    def getLogger(self):
        if not self._log:
            self._log = self.getManager().getLogger()
        if not self._log:
            self._log = logging.getLogger(self.__class__.__name__)
            self._log.setLevel(logging.ERROR)
            self._log.addHandler(logging.StreamHandler(sys.stderr))
        return self._log

    def getOperationsCount(self):
        return self._op_count

    def getAllOperationsCount(self):
        s = 0
        for op, c in self._op_count.items():
            s += c
        return s

    def incOperationsCount(self, op):
        if not (op in self._op_count):
            self._op_count[ op ] = 0
        self._op_count[ op ] += 1
        return self

    def getTimeSpent(self):
        return self._time_spent

    def getAllTimeSpent(self):
        s = 0
        for op, t in self._time_spent.items():
            s += t
        return s

    def incOperationsTimeSpent(self, op, start_time):
        if not (op in self._time_spent):
            self._time_spent[ op ] = 0
        self._time_spent[ op ] += time() - start_time
        return self

    def startTimer(self):
        self._last_time = time()
        return self

    def stopTimer(self, op):
        # Too slow =(
        # caller = inspect.currentframe().f_back
        # op = inspect.getframeinfo(caller)[2]

        self.incOperationsCount(op)
        self.incOperationsTimeSpent(op, self._last_time)

        self._last_time = None
        return self

    def getName(self):
        return self._table_name

    def setName(self, tableName):
        self._table_name = tableName
        return self

    def getManager(self):
        return self._manager

    def getDbFilePath(self):
        if not self._db_file_path:
            self._db_file_path = os.path.join(
                self.getManager().getBasePath(),
                self.getManager().getDbName(),
                "%s.sqlite3" % self.getName()
            )
            self._db_file_path = os.path.abspath(self._db_file_path)
        return self._db_file_path

    def connect( self ):
        import sqlite3

        db_path = self.getDbFilePath()

        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        isNew = False
        pageSize = self._page_size
        if os.path.isfile(db_path):
            fileSize = os.path.getsize(db_path)
        else:
            isNew = True
            fileSize = 0
        filePageSize = fileSize / 2147483646.0 * 1.05
        while pageSize < filePageSize:
            pageSize *= 2
            if pageSize >= 64*1024:
                break

        cacheSize = 64*1024*1024 / pageSize

        conn = sqlite3.connect(db_path)

        conn.row_factory = dict_factory
        conn.text_factory = bytes

        conn.execute('PRAGMA locking_mode=NORMAL')
        if not self.getManager().getSynchronous():
            conn.execute("PRAGMA synchronous=OFF")

        conn.execute("PRAGMA temp_store=FILE")
        conn.execute("PRAGMA max_page_count=2147483646")
        conn.execute("PRAGMA page_size=%i" % pageSize)
        conn.execute("PRAGMA cache_size=%i" % cacheSize)
        conn.execute("PRAGMA journal_mode=WAL")

        if not self.getManager().getAutocommit():
            conn.execute("PRAGMA read_uncommitted=ON")
            conn.isolation_level = "DEFERRED"
        else:
            conn.isolation_level = None

        self._conn = conn

        if isNew:
            self.create()
        return

    def getConnection(self):
        if self._conn is None:
            self.connect()
        return self._conn

    def getCursor(self, new=False):
        cur = self._curr
        if new:
            cur = self.getConnection().cursor()
            return cur
        if not self._curr:
            cur = self._curr = self.getConnection().cursor()
        return cur

    def getPageSize(self):
        result = self.getConnection().execute('PRAGMA page_size').fetchone()
        # print("%s::getPageSize()=%r" % (self.getName(), result,))
        return result["page_size"]

    def getPageCount(self):
        result = self.getConnection().execute('PRAGMA page_count').fetchone()
        # print("%s::getPageCount()=%r" % (self.getName(), result,))
        return result["page_count"]

    def getFileSize(self):
        db_path = self.getDbFilePath()
        if os.path.isfile(db_path):
            return os.stat(db_path).st_size
        return 0

    def getSize(self):
        return self.getPageSize() * self.getPageCount()

    def clean( self ):
        self.startTimer()
        cur = self.getCursor()
        cur.execute("TRUNCATE `%s`" % self.getName())
        self.stopTimer("clean")
        return self

    def create( self ):
        raise NotImplemented

    def begin( self ):
        if not self.getManager().getAutocommit():
            cur = self.getCursor()
            cur.execute("BEGIN")
        return self

    def commit(self):
        if not self.getManager().getAutocommit():
            self.startTimer()
            cur = self.getCursor()
            try:
                cur.execute("COMMIT")
            except:
                pass
            self.stopTimer("commit")
        return self

    def rollback(self):
        if not self.getManager().getAutocommit():
            self.startTimer()
            self.getConnection().rollback()
            self.stopTimer("rollback")
        return self

    def vacuum(self):
        self.startTimer()
        #cur = self.getCursor()
        #cur.execute("VACUUM")
        self.close()

        # VACUUM breaks on huge DB
        # Dump/Load DB
        # Warning! Need 3+x space!

        fn = self.getDbFilePath()
        if not os.path.isfile(fn):
            # Nothing to do
            return self

        oldSize = os.path.getsize(fn)

        bkp_fn = fn + ".bkp"

        os.rename(fn, bkp_fn)

        p1 = subprocess.Popen(["sqlite3", bkp_fn, ".dump"], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["sqlite3", fn], stdin=p1.stdout, stdout=open(os.devnull,"w"))

        ret = p1.wait() > 0 or p2.wait() > 0
        if ret:
            if os.path.isfile(fn):
                os.unlink(fn)
            os.rename(bkp_fn, fn)
            self.getLogger().error("Can't dump sqlite3 db: %s" % self.getName())
            return self

        os.unlink(bkp_fn)

        newSize = os.path.getsize(fn)

        diffSign = newSize > oldSize and '+' or '-'

        sz = format_size(abs(newSize - oldSize))

        self.getLogger().info("DB '%s' size change after vacuum: %s%.2f%% (%s%s)" % (
            self.getName(), diffSign, abs(newSize - oldSize) * 100.0 / oldSize, diffSign, sz,))

        self.stopTimer("vacuum")
        return self

    def close(self):
        if self._curr:
            self._curr.close()
            self._curr = None
        if self._conn:
            self._conn.close()
            self._conn = None
        return self

    def createIndexIfNotExists(self, indexName, fieldList, unique=False, indexSizes=None):
        """
        @param indexName: Index name
        @param fieldList: List of table fields for index
        @param unique: Is index unique?
        @param indexSizes: Sizes for CHAR/BINARY/BLOB/TEXT indexes. How many starting symbols to index

        @type indexName: str
        @type fieldList: list|tuple
        @type unique: bool
        @type indexSizes: dict
        """
        if not len(fieldList):
            raise ValueError("Define table field list for index!")

        cur = self.getCursor()

        cur.execute(
            "PRAGMA index_info(`%s`);" %
            (self.getName()+"_" + indexName,)
        )
        row = cur.fetchone()

        exists = (row is not None) and (len(row) > 0)

        if not exists:
            _u = ""
            if unique:
                _u = "UNIQUE"

            _f = ()

            if not indexSizes or type(indexSizes) is not dict:
                indexSizes = {}

            for field in fieldList:

                _isz = ""
                sz = indexSizes.get(field, 0)
                if sz > 0:
                    _isz = "(%d)" % sz

                _f += ("`%s`%s" % (field, _isz,),)

            _f = ",".join(_f)

            cur.execute(
                "CREATE "+_u+" INDEX `%s` " % (self.getName() + "_" + indexName)+
                " ON `%s` " % self.getName()+
                "("+_f+")")

        return exists

    def drop(self):
        self.startTimer()
        self.close()
        if os.path.isfile(self.getDbFilePath()):
            os.unlink(self.getDbFilePath())
        self.stopTimer("drop")
        return self

    pass