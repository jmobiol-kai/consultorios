##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""El color era un texto. Pasa a color anotado antes de que el ORM
intente leer esa columna como un many2one.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'emr_pet'
           AND column_name = 'color'
        """
    )
    row = cr.fetchone()
    if not row or row[0] not in ("character varying", "text"):
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'emr_pet'
           AND column_name = 'color_note'
        """
    )
    if cr.fetchone():
        return
    cr.execute("ALTER TABLE emr_pet RENAME COLUMN color TO color_note")
