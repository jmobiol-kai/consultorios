##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Saca la tabla de fichas antes de que el modelo pase a ser una vista.

19.0.1.18.0 creaba filas al abrir el odontograma. La vista usa el mismo
nombre. Si la tabla sigue, CREATE VIEW falla.
"""


def migrate(cr, version):
    cr.execute("DROP TABLE IF EXISTS emr_odontogram_page CASCADE")
