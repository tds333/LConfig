import io
import inspect

import pytest
from lconfig import LConfig, LConfigProxy, Adapter, Converter

TESTDATA = """
# commnet

# test adapters
.adapt.listing = listing

# test converters
.convert.list. = stringlist
.convert.list = stringlist
.convert.listing = stringlist
.convert.interpolate. = interpolate

# test default
.default.dkey = default
.adapt.dkey = append_default

# test config data
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
interpolate.d.1 = 1
interpolate.d = $interpolate.d.1 ${interpolate.d.1} $$

namespace.a = 1
namespace.b = 2
namespace.c.1 = one
"""

TESTDATA_SEC = """
# commnet
.convert.isec. = interpolate

# test config data
key = value

[section]
key = value_sec
int = 11
 = 2

[isec]
interpolate.a = ${section.key} is the value of key
"""


@pytest.fixture
def testfile():
    from pathlib import Path

    testdir = Path(__file__).parent
    test1_file = testdir / "test1.cfg"
    yield test1_file


@pytest.fixture
def cfg():
    cfg = LConfig()
    cfg.read_data(TESTDATA.splitlines())
    yield cfg


def test_import_all():
    import lconfig

    assert set(lconfig.__all__) == set(
        ["LConfig", "LConfigProxy", "Adapter", "Converter"]
    )


class TestLConfig:
    def test_init(self):
        cfg = LConfig()
        assert len(cfg) == 0

    def test_read_data(self):
        cfg = LConfig()
        cfg.read_data(TESTDATA.splitlines())
        assert cfg.key == "value"
        cfg = LConfig()
        cfg.read_data(io.StringIO(TESTDATA))
        assert cfg.key == "value"

    def test_read_data_sec(self):
        cfg = LConfig()
        cfg.read_data(TESTDATA_SEC.splitlines())
        print(cfg)
        assert cfg.key == "value"
        assert cfg.section.key == "value_sec"

    def test_read_dict(self):
        cfg = LConfig()
        cfg.read_dict({"a": "b"})
        assert cfg["a"] == "b"

    def test_read_dict_level(self):
        cfg = LConfig()
        cfg.read_dict({"a": {"1": "one", "2": "two"}})
        assert cfg["a.1"] == "one"
        assert cfg["a.2"] == "two"

    def test_read_dict_list(self):
        cfg = LConfig()
        cfg.read_dict({"a": ["1", "2"], "b": ["eins", "zwei"]})
        assert cfg["a"] == "2"
        assert cfg["b"] == "zwei"
        assert cfg.get_raw("a") == ["1", "2"]

    def test_write_data(self):
        cfg = LConfig()
        cfg["key"] = "value"
        output = io.StringIO()
        cfg.write_data(output)
        assert output.getvalue() == "key = value\n"

    def test_convert(self, cfg):
        assert isinstance(cfg.list, list)
        assert len(cfg.list) == 3
        assert cfg.list == ["1", "2", "3"]

    def test_adapt(self, cfg):
        assert isinstance(cfg.listing, list)
        assert len(cfg.listing) == 7
        assert cfg.listing == ["1", "2", "3", "4", "5", "6", "7"]

    def test_access(self, cfg):
        assert cfg.key == "value"
        assert cfg["key"] == "value"

    def test_get_raw(self, cfg):
        assert cfg.get_raw("list.a") == ["1", "2"]

    def test_interpolate(self, cfg):
        value = cfg.interpolate.a
        assert value == "value is the value of key"
        value = cfg.interpolate.b
        assert value == "value is the value of key is 2"
        value = cfg.interpolate.c
        assert value == "true"
        assert cfg.interpolate.d == "1 1 $"

    def test_iter(self, cfg):
        assert len(list(iter(cfg))) > 0

    def test_adapter_names(self, cfg):
        adapters = [m[0] for m in inspect.getmembers(Adapter, inspect.isfunction)]
        assert cfg.adapter_names() == adapters

    def test_converter_names(self, cfg):
        converters = [m[0] for m in inspect.getmembers(Converter, inspect.isfunction)]
        assert cfg.converter_names() == converters

    def test_resolve_name(self):
        TESTDATA = """
        .test. = l0
        .test.l1. = l1
        .test.l.l2. = l2
        .test.s.l1 = lvl1
        """
        cfg = LConfig()
        cfg.read_data(io.StringIO(TESTDATA))
        name = cfg.resolve_name(key="", prefix="", default="")
        assert name == ""
        name = cfg.resolve_name(key="", prefix="", default="d")
        assert name == "d"
        name = cfg.resolve_name(key="d", prefix="", default=None)
        assert name is None
        assert cfg.resolve_name("key.a", ".test") == "l0"
        assert cfg.resolve_name("key.a.b.c", ".test") == "l0"
        assert cfg.resolve_name("l1.a", ".test") == "l1"
        assert cfg.resolve_name("l1.a.b.c", ".test") == "l1"
        assert cfg.resolve_name("l.l2.a", ".test") == "l2"
        assert cfg.resolve_name("l.l2.a.b.c", ".test") == "l2"
        assert cfg.resolve_name("s.l1", ".test") == "lvl1"
        assert cfg.resolve_name("s.l1.5", ".test") == "l0"
        assert cfg.resolve_name("z.l1.5", ".testoff", "default") == "default"

    def test_read_file(self, testfile):
        cfg = LConfig()
        cfg.read_file(testfile)
        assert cfg.key == "value"

    def test_default(self, cfg):
        cfg["dkey"] = "xyz"
        assert cfg["dkey"] == "xyz"
        cfg["dkey"] = ""
        assert cfg["dkey"] == "default"

    def test_items(self, cfg):
        for key, value in cfg.items():
            assert isinstance(key, str)

    def test_performance(self):
        cfg = LConfig()
        for i in range(1000):
            key = f"key_{i}"
            value = f"value for {i}"
            cfg[key] = value
        for key, value in cfg.items():
            assert isinstance(key, str)


class TestLConfigProxy:
    def test_init(self, cfg):
        proxy = LConfigProxy(cfg)
        assert proxy.key == "value"

    def test_init_part(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert proxy.a == "1"
        assert proxy["a"] == "1"

    def test_getitem(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert proxy["c.1"] == "one"

    def test_setitem(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        proxy["d"] = "dee"
        assert proxy["d"] == "dee"

    def test_delitem(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert proxy["a"] == "1"
        del proxy["a"]
        with pytest.raises(KeyError):
            proxy["a"]

    def test_getattr(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert proxy.a == "1"
        with pytest.raises(AttributeError):
            proxy.notthere

    def test_iter(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert list(iter(proxy)) == ["a", "b", "c.1"]

    def test_contains(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert "a" in proxy

    def test_get_prefix(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert proxy.get_prefix() == "namespace."


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
