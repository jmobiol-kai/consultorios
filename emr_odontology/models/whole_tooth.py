##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Qué estados de fábrica pintan la pieza entera.

El mapa no mira el nombre: lee el campo `whole_tooth` del catálogo.
Esto solo sirve para prender esa marca la primera vez en filas que ya
existen (el xml es noupdate y un -u no las reescribe). Cubre el código
de fábrica y las grafías habituales, con o sin acento: Protesis,
Prótesis, Extraccion indicada, Extracción indicada.
"""
import re
import unicodedata

# Códigos que ya vienen con el módulo. El nombre se puede cambiar en
# Configuración; el código no.
FACTORY_WHOLE_TOOTH_CODES = frozenset({
    "sound",
    "crown",
    "implant",
    "extraction",
    "missing",
    "prosthesis",
})

# Nombres plegados (sin acento, en minúscula). Un estado cargado a mano
# como "Protesis" o "Extracción indicada" entra por acá.
WHOLE_TOOTH_NAMES = frozenset({
    "sano",
    "corona",
    "implante",
    "ausente",
    "protesis",
    "extraccion",
    "extraccion indicada",
})


def fold_label(value):
    """Minúsculas, sin acentos ni signos. «Prótesis» y «protesis» empatan."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def name_is_whole_tooth(name):
    folded = fold_label(name)
    if not folded:
        return False
    if folded in WHOLE_TOOTH_NAMES:
        return True
    # «Prótesis fija», «Implante dental», «Extracción indicada (urgencia)».
    return any(folded.startswith(base + " ") for base in WHOLE_TOOTH_NAMES)


def matches_whole_tooth(code, name):
    """True si esta fila de catálogo tiene que nacer como pieza entera."""
    normalized = (code or "").strip().lower()
    if normalized in FACTORY_WHOLE_TOOTH_CODES:
        return True
    return name_is_whole_tooth(name)
