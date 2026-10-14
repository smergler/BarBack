from evals.fixtures import INVENTORY as EVAL_INV
from recommender.inventory_match import match_bottle
from recommender.schemas import Bottle

INV = [
    Bottle(id="1", name="Four Roses Small Batch", category="bourbon"),
    Bottle(id="2", name="Rittenhouse Rye", category="rye"),
    Bottle(id="4", name="Campari", category="liqueur"),
    Bottle(id="5", name="Carpano Antica Sweet Vermouth", category="vermouth"),
    Bottle(id="6", name="Dolin Dry Vermouth", category="vermouth"),
]


def _name(b):
    return b.name if b else None


def test_exact_and_partial_matches():
    assert _name(match_bottle("Four Roses Small Batch", INV)) == "Four Roses Small Batch"
    # stopwords (small, batch) dropped, still matches on four/roses
    assert _name(match_bottle("Four Roses", INV)) == "Four Roses Small Batch"
    assert _name(match_bottle("Rittenhouse", INV)) == "Rittenhouse Rye"
    assert _name(match_bottle("Campari", INV)) == "Campari"


def test_generic_name_matches_owned_specific_bottle():
    # user owns Carpano Antica; a recipe calling for "sweet vermouth" is grounded
    assert _name(match_bottle("sweet vermouth", INV)) == "Carpano Antica Sweet Vermouth"
    assert _name(match_bottle("dry vermouth", INV)) == "Dolin Dry Vermouth"


def test_unowned_spirits_do_not_match():
    assert match_bottle("white rum", INV) is None
    assert match_bottle("Tequila Blanco", INV) is None
    assert match_bottle("Aperol", INV) is None


def test_generic_category_word_alone_does_not_match():
    # owning Angostura Bitters must NOT make Peychaud's Bitters look owned
    inv = INV + [Bottle(id="7", name="Angostura Bitters", category="bitters")]
    assert match_bottle("Peychaud's Bitters", inv) is None
    assert match_bottle("Angostura Bitters", inv).name == "Angostura Bitters"
    # but the qualifier still carries sweet/dry vermouth to the owned bottle
    assert match_bottle("sweet vermouth", inv).name == "Carpano Antica Sweet Vermouth"


def test_campari_does_not_match_generic_amaro():
    inv = INV + [Bottle(id="10", name="Campari", category="liqueur", subcategory="amaro")]
    assert match_bottle("Amaro Nonino", inv) is None


def test_empty_and_stopword_only_names():
    assert match_bottle("", INV) is None
    assert match_bottle("the of and", INV) is None


# --- category fallback + weak-token tests against the eval fixture inventory ---

def test_orange_bitters_does_not_match_cointreau():
    # "orange bitters" → tokens = {"orange"} (bitters is stopword)
    # Cointreau has subcategory="orange" but name token "cointreau" ≠ "orange"
    # — must not match via either name or weak-token path.
    assert match_bottle("orange bitters", EVAL_INV) is None


def test_bourbon_category_fallback_matches_four_roses():
    # "bourbon" doesn't appear in "Four Roses Small Batch" name tokens
    # → category fallback must fire and return the bourbon bottle.
    b = match_bottle("bourbon", EVAL_INV)
    assert b is not None
    assert b.name == "Four Roses Small Batch"


def test_rye_still_matches_rittenhouse():
    # "rye" overlaps with "Rittenhouse Rye" on the name token "rye" —
    # must still work after the weak-token and category-fallback changes.
    b = match_bottle("rye", EVAL_INV)
    assert b is not None
    assert b.name == "Rittenhouse Rye"


def test_peychauds_bitters_does_not_match():
    # "Peychaud's Bitters" → tokens = {"peychauds"} (bitters is stopword)
    # No owned bottle has "peychauds" in its name tokens.
    assert match_bottle("Peychaud's Bitters", EVAL_INV) is None


def test_gin_rum_vodka_tequila_category_fallback():
    # None of these ingredient names overlap the owned bottles' name tokens —
    # only the category fallback (now that rum/gin/vodka/tequila are no
    # longer stripped as stopwords) can ground them.
    inv = [
        Bottle(id="11", name="Hendrick's Gin", category="gin"),
        Bottle(id="12", name="Diplomatico Reserva", category="rum"),
        Bottle(id="13", name="Tito's Handmade", category="vodka"),
        Bottle(id="14", name="Espolòn Blanco", category="tequila"),
    ]
    assert match_bottle("gin", inv).name == "Hendrick's Gin"
    assert match_bottle("rum", inv).name == "Diplomatico Reserva"
    assert match_bottle("vodka", inv).name == "Tito's Handmade"
    assert match_bottle("tequila", inv).name == "Espolòn Blanco"


def test_weak_token_prevents_false_name_match():
    # "aged" overlaps "Aged Rum Reserve"'s name tokens at score 0.5 (passes the
    # 0.5 threshold), but "aged" is in _WEAK_TOKENS so the name-match is
    # rejected; category fallback doesn't apply either ("aged" isn't a
    # category word, so "aged tequila" isn't a purely generic ask), so the
    # result is correctly None. If _WEAK_TOKENS were emptied, this ingredient
    # would wrongly match "Aged Rum Reserve" via the name-overlap path.
    inv = INV + [Bottle(id="15", name="Aged Rum Reserve", category="rum")]
    assert match_bottle("aged tequila", inv) is None
