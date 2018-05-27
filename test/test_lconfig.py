import io

import pytest
from lconfig import Config, ConfigProxy

TESTDATA = """
# commnet
.convert.list. = stringlist
.convert.list = stringlist
.adapt.listing = listing
.convert.listing = stringlist
.convert.interpolate. = interpolate
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

interpolate.a = ${key} is the value of key
interpolate.b = ${interpolate.a} is 2
interpolate.c = $bool

namespace.a = 1
namespace.b = 2
namespace.c.1 = one
"""


@pytest.fixture
def cfg():
    cfg = Config()
    cfg.read_data(TESTDATA.splitlines())
    yield cfg


def test_init():
    cfg = Config()
    assert len(cfg) == 0


def test_read_data():
    cfg = Config()
    cfg.read_data(TESTDATA.splitlines())
    assert cfg.key == "value"
    cfg = Config()
    cfg.read_data(io.StringIO(TESTDATA))
    assert cfg.key == "value"


def test_read_dict():
    cfg = Config()
    cfg.read_dict({"a": "b"})
    assert cfg["a"] == "b"


def test_read_dict_level():
    cfg = Config()
    cfg.read_dict({"a": {"1": "one", "2": "two"}})
    assert cfg["a.1"] == "one"
    assert cfg["a.2"] == "two"


def test_read_dict_list():
    cfg = Config()
    cfg.read_dict({"a": ["1", "2"], "b": ["eins", "zwei"]})
    assert cfg["a"] == "2"
    assert cfg["b"] == "zwei"
    assert cfg.get_raw("a") == ["1", "2"]


def test_write_data():
    cfg = Config()
    cfg["key"] = "value"
    output = io.StringIO()
    cfg.write_data(output)
    assert output.getvalue() == "key = value\n"


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


def test_interpolate(cfg):
    value = cfg.interpolate.a
    assert value == "value is the value of key"
    value = cfg.interpolate.b
    assert value == "value is the value of key is 2"
    value = cfg.interpolate.c
    assert value == "true"


def test_iter(cfg):
    assert len(list(iter(cfg))) > 0


def test_iter_proxy(cfg):
    proxy = cfg.interpolate
    assert list(iter(proxy)) == ["a", "b", "c"]


class TestConfigProxy:

    def test_init(self, cfg):
        proxy = ConfigProxy(cfg)
        assert proxy.key == "value"

    def test_init_part(self, cfg):
        proxy = ConfigProxy(cfg, prefix="namespace.")
        assert proxy.a == "1"
        assert proxy["a"] == "1"

    def test_getitem(self, cfg):
        proxy = ConfigProxy(cfg, prefix="namespace.")
        assert proxy["c.1"] == "one"

    def test_setitem(self, cfg):
        proxy = ConfigProxy(cfg, prefix="namespace.")
        proxy["d"] = "dee"
        assert proxy["d"] == "dee"

    def test_delitem(self, cfg):
        proxy = ConfigProxy(cfg, prefix="namespace.")
        assert proxy["a"] == "1"
        del proxy["a"]
        with pytest.raises(KeyError):
            proxy["a"]

    def test_getattr(self, cfg):
        proxy = ConfigProxy(cfg, prefix="namespace.")
        assert proxy.a == "1"
        with pytest.raises(AttributeError):
            proxy.notthere


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
