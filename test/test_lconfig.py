import pytest
from lconfig import Config

TESTDATA = """
# commnet
.convert.list. = stringlist
.convert.list = stringlist
.adapt.listing = listing
.convert.listing = stringlist
key = value
key2 = value
dot.key = more value
bool = true
int = 11
float = 1.5
list = 1
 = 2
list = 3
list.a = 1
list.a = 2

reset = 1
reset = 2
reset = 3
reset =

listing = 1,2,3,4
= 5,6,7

#inval_id = 5
"""


@pytest.fixture
def cfg():
    cfg = Config()
    cfg.read_data(TESTDATA)
    yield cfg


def test_init():
    cfg = Config()
    assert len(cfg) == 0


def test_read_data():
    cfg = Config()
    cfg.read_data(TESTDATA)
    assert cfg.key == "value"


def test_convert(cfg):
    assert isinstance(cfg.list, list)
    assert len(cfg.list) == 3
    assert cfg.list == ["1", "2", "3"]


def test_adapt(cfg):
    assert isinstance(cfg.listing, list)
    assert len(cfg.listing) == 7
    assert cfg.listing == ["1", "2", "3", "4", "5", "6", "7"]


def test_access(cfg):
    assert cfg.key == "value"
    assert cfg["key"] == "value"


def test_get_raw(cfg):
    assert cfg.get_raw("list.a") == ["1", "2"]


def off():
    print(cfg["list"])
    print(cfg["list.a"])
    print(cfg)
    print(cfg.key)
    print(cfg.dot)
    print(cfg.dot.key)
    try:
        cfg.dot.bla
    except AttributeError as ex:
        print(ex)
    try:
        cfg["dot.bla"]
    except KeyError as ex:
        print(ex)
