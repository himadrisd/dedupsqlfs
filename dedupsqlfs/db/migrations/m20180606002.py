# -*- coding: utf8 -*-
#
# DB migration 002 by 2018-06-06
#
# Table `name` uses md5 hash as BINARY(16) now
#
__author__ = 'sergey'

__NUMBER__ = 20180606002

def run(manager):
    """
    :param manager: Database manager
    :type  manager: dedupsqlfs.db.sqlite.manager.DbManager|dedupsqlfs.db.mysql.manager.DbManager
    :return: bool
    """

    try:
        table_nm = manager.getTable("name")
        """
        :type table_name: dedupsqlfs.db.sqlite.table.subvolume.TableName |
                        dedupsqlfs.db.mysql.table.subvolume.TableName
        """

        from dedupsqlfs.lib.constants import ROOT_SUBVOLUME_NAME

        manager.getLogger().info("Migration #%s" % (__NUMBER__,))

        manager.getLogger().info("Migrate name table")

        cur = table_nm.getCursor(True)

        # Rename table to _old
        manager.getLogger().info("Rename old table")
        if manager.TYPE == "mysql":
            cur.execute("RENAME TABLE `%s` TO `%s_old`;" % (table_nm.getName(),table_nm.getName(),))
        if manager.TYPE == "sqlite":
            cur.execute("ALTER TABLE `%s` RENAME TO `%s_old`;" % (table_nm.getName(), table_nm.getName(),))
            # Sqlite indexes not connected to tables
            table_nm.createIndexOnTableIfNotExists("%s_old" % table_nm.getName(), "hash", ("hash",), True)
            table_nm.dropIndex("hash")

        # Create new table
        manager.getLogger().info("Create new table")
        table_nm.create()

        cur.execute("SELECT * FROM `%s_old`" % table_nm.getName())

        for nm in iter(cur.fetchone, None):

            table_nm.insertRaw(nm['id'], nm['value'])

        table_nm.commit()

        manager.getLogger().info("Drop old table")
        cur.execute("DROP TABLE `%s_old`;" % (table_nm.getName(),))
        if manager.TYPE == "sqlite":
            # Sqlite indexes not connected to tables
            table_nm.dropIndexOnTable("%s_old" % table_nm.getName(), "hash")

        table_nm.commit()
        table_nm.close()


    except Exception as e:
        import traceback
        manager.getLogger().error("Migration #%s error: %s" % (__NUMBER__, e,))
        manager.getLogger().error("Migration #%s trace:\n%s" % (__NUMBER__, traceback.format_exc(),))
        return False

    table_opts = manager.getTable("option")

    table_opts.getCursor()

    mignumber = table_opts.get("migration")
    if not mignumber:
        table_opts.insert("migration", __NUMBER__)
    else:
        table_opts.update("migration", __NUMBER__)

    table_opts.commit()

    return True
