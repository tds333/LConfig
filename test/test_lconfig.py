import io
import inspect

import pytest
from lconfig import (
    LConfig,
    LConfigProxy,
    Adapter,
    Converter,
    TolerantParser,
    SimpleIniParser,
)


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

# json testing
.adapt.json. = json
.convert.json. = json
.convert.cjson. = json

# test config data
key = value
key2 = value
dot.key = more value
bool = true
int = 11
float = 1.5
list = 1
list = 2
list = 3
list.a = 1
list.a = 2

reset = 1
reset = 2
reset = 3
reset =

listing = 1,2,3,4
listing = 5,6,7

interpolate.a = ${key} is the value of key
interpolate.b = ${interpolate.a} is 2
interpolate.c = $bool
interpolate.d.1 = 1
interpolate.d = $interpolate.d.1 ${interpolate.d.1} $$

namespace.a = 1
namespace.b = 2
namespace.c.1 = one

empty_new_key =

new_key_second =
new_key_second = one
new_key_second = two

json.list = [1,2]
json.int = 1
json.str = "abc"
json.object = {"a": "b"}
json.float = 3.14
json.null = null
json.bool = true

cjson.list = [1,2,3, "a"]
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
        cfg = LConfig()
        cfg.read_data(TESTDATA)
        assert cfg.key == "value"

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

    def test_getitem(self, cfg):
        assert cfg["key"] == "value"

    def test_setitem(self):
        cfg = LConfig()
        cfg["adf"] = "my value"
        assert cfg["adf"] == "my value"

    def test_getitem_dot(self, cfg):
        proxy = cfg["namespace."]
        assert proxy.a == "1"
        with pytest.raises(KeyError):
            proxy["notthere"]

    def test_getitem_dot_empty(self, cfg):
        proxy = cfg["namespaces."]
        with pytest.raises(KeyError):
            proxy["notthere"]

    def test_assign_proxy(self):
        cfg = LConfig()
        proxy = cfg["section."]
        proxy["a"] = 5
        assert cfg["section.a"] == "5"

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

    def test_empty_new_key(self, cfg):
        assert "empty_new_key" not in cfg

    def test_new_key_second(self, cfg):
        assert "new_key_second" in cfg
        assert cfg.get_raw("new_key_second") == ["one", "two"]

    def test_json(self, cfg):
        assert cfg.json.list == [1, 2]
        assert cfg["json.int"] == 1
        assert cfg["json.str"] == "abc"
        assert cfg["json.float"] == 3.14
        assert cfg["json.object"] == {"a": "b"}
        assert cfg["json.bool"] is True
        assert cfg["json.null"] is None
        assert cfg["cjson.list"] == [1, 2, 3, "a"]
        cfg["json.myvalue"] = {"a": [1, True, 0.0, None]}
        assert cfg["json.myvalue"] == {"a": [1, True, 0.0, None]}


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

    def test_setitem(self):
        cfg = LConfig().read_data(TESTDATA)
        proxy = LConfigProxy(cfg, prefix="namespace.")
        proxy["d"] = "dee"
        assert proxy["d"] == "dee"
        with pytest.raises(ValueError):
            proxy["  e   "] = "ee"

    def test_setitem_error(self):
        cfg = LConfig().read_data(TESTDATA)
        proxy = LConfigProxy(cfg, prefix="namespace.")
        with pytest.raises(ValueError):
            proxy["§$%§d"] = "dee"

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

    def test_setattr(self):
        cfg = LConfig()
        cfg["a"] = "a"
        assert cfg.a == "a"
        cfg.a = "b"
        assert cfg.a == "b"

    def test_setattr_error(self):
        cfg = LConfig()
        proxy = cfg["namespace."]
        with pytest.raises(AttributeError):
            proxy.a = "b"

    def test_iter(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert list(iter(proxy)) == ["a", "b", "c.1"]

    def test_contains(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert "a" in proxy

    def test_get_prefix(self, cfg):
        proxy = LConfigProxy(cfg, prefix="namespace.")
        assert proxy.get_prefix() == "namespace."

    def test_read_data(self):
        cfg = LConfig()
        proxy = LConfigProxy(cfg, prefix="namespace.")
        proxy.read_data("key = value")
        assert proxy.key == "value"
        assert list(proxy) == ["key"]


TESTDATA_TOLERANT = """
# test tolerant config format
KEY = value

KEY.2 = value_sec
int = 11
= 2
"""


@pytest.fixture
def tcfg():

    class TConfig(LConfig):
        PARSER = TolerantParser

    cfg = TConfig()
    cfg.read_data(TESTDATA_TOLERANT)
    yield cfg


class TestTolerantParser:
    pass


TESTDATA_INI = """
# test ini style
key = value

[section]
key = value_sec
int = 2

[sec2]
key = v

[multi]
line = line1
    line2
    line3
"""


@pytest.fixture
def ini_cfg():

    class IniAdapter(Adapter):
        default = Adapter.append

    class IniConverter(Converter):
        default = Converter.stringjoin

    class IniConfig(LConfig):
        PARSER = SimpleIniParser
        ADAPTER = IniAdapter
        CONVERTER = IniConverter

    cfg = IniConfig()
    cfg.read_data(TESTDATA_INI)
    yield cfg


class TestSimpleIniParser:

    def test_read_data_sec(self, ini_cfg):
        assert ini_cfg.key == "value"
        assert ini_cfg.section.key == "value_sec"

    def test_double_assign(self, ini_cfg):
        assert ini_cfg["section.int"] == "2"

    def test_multiline(self, ini_cfg):
        assert ini_cfg["multi.line"] == "line1\nline2\nline3"
