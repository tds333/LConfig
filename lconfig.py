# lconfig parsing and more
import string
from pprint import pformat
from collections import OrderedDict
from collections.abc import MutableMapping, Mapping
from copy import deepcopy
import inspect

_KEY_CHARS = string.ascii_lowercase
_KEY_CHARS += string.digits
_KEY_CHARS += "."
_KEY_CHARS = frozenset(_KEY_CHARS)

# hint to get functions from a class
# inspect.getmembers(cls, inspect.isfunction)


class Adapters:

    @staticmethod
    def default(key, values, value):
        value = value.strip()
        if value:
            values.append(value)
        else:
            return None  # delete key
        return values

    @staticmethod
    def listing(key, values, value):
        value = value.strip()
        listing = value.split(",")
        if listing:
            values.extend(listing)
        return values

    @staticmethod
    def overwrite(key, values, value):
        value = value.strip()
        return [value]

    dot = overwrite


class Converters:

    BOOLEAN_STATES = {
        "1": True,
        "yes": True,
        "true": True,
        "on": True,
        "0": False,
        "no": False,
        "false": False,
        "off": False,
    }

    @staticmethod
    def default(key, values):
        if values:
            return str(values[-1])
        return None

    @staticmethod
    def raw(key, values):
        return values

    @staticmethod
    def boolean(key, values):
        last_value = values[-1].lower()
        return Converters.BOOLEAN_STATES.get(last_value, False)

    @staticmethod
    def integer(key, values):
        return int(values[-1])

    @staticmethod
    def floatingpoint(key, values):
        return float(values[-1])

    @staticmethod
    def stringlist(key, values):
        return [str(v) for v in values]

    dot = default


# a .default specified as string
# .type specifies the type of the value (str, int, bool, ...), see typing
# the converter should return this type of value
# .adapt specifies as string reference to an adapter function
# an adapter should only output one valid string value for the key
# optionally it can be checked if it is valid with the right type
# .convert specifies as string reference to a converter function
# a converter gets a list of string value and returns a valid type
# for this key, this must not be a string


# setting a value
# 1. call adapter with value
# 2. set return value from adapter

# getting a value
# 1. get value or default
# 2. call converter
# 3. return value from converter


class ConfigProxy(MutableMapping):

    def __init__(self, config, part):
        self._config = config
        self._part = part

    def __getitem__(self, key):
        return self._config[self._part + key]

    def __setitem__(self, key, value):
        key = self._part + key
        self._config[key] = value

    def __delitem__(self, key):
        key = self._part + key
        del self._config[key]

    def __iter__(self):
        for key in self._config:
            if key.startswith(self._part):
                yield key

    def __len__(self):
        return len(list(iter(self)))
        # return len(self._config)

    def __getattr__(self, name):
        return self._config.__getattr__(self._part + name)


class Config(MutableMapping):

    KEY_CHARS = _KEY_CHARS
    # default_prefix = ".default"
    # validator_prefix = ".validate"
    adapter_prefix = ".adapt"
    converter_prefix = ".convert"

    def __init__(self):
        self._data = OrderedDict()
        self._adapter = {}
        self._converter = {}
        adapters = dict(inspect.getmembers(Adapters, inspect.isfunction))
        converters = dict(inspect.getmembers(Converters, inspect.isfunction))
        self.register_adapters(adapters)
        self.register_converters(converters)

    @classmethod
    def adapt_key(cls, key):
        assert isinstance(key, str)
        key = key.strip()
        not_allowed_chars = set(key) - cls.KEY_CHARS
        if not_allowed_chars:
            raise ValueError(
                "Detected not allowed character(s): %r in key %r."
                % ("".join(not_allowed_chars), key)
            )
        return key

    def get_raw(self, key):
        return self._data[key]

    def raw_dict(self):
        return deepcopy(self._data)

    def __getitem__(self, key):
        try:
            values = self._data[key]
        except KeyError as ex:
            raise KeyError("Key %r not found in %r." % (key, self.__class__.__name__))
        converter = self.get_converter(key)
        return converter(key, values)

    def __setitem__(self, key, value):
        key = self.adapt_key(key)
        if key in self._data:
            values = self._data[key]
        else:
            values = []
        adapter = self.get_adapter(key)
        values = adapter(key, values, value)
        if values is None:
            del self._data[key]
        else:
            self._data[key] = values

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            pass
        dotname = name + "."
        for key in self:
            if key.startswith(dotname):
                return ConfigProxy(config=self, part=dotname)
        raise AttributeError("Config key %r not found." % name)

    def read_file(self, file):
        with open(file, mode="r", encoding="utf8") as config_file:
            self.read_data(config_file)

    def read_data(self, data):
        last_key = ""
        for line in data.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            key, _, value = line.partition("=")
            if key:  # allows empty key be same as last key
                last_key = key
            else:
                key = last_key
            self[key] = value

    def read_dict(self, data, level=""):
        for key in data:
            value = data[key]
            if isinstance(value, Mapping):
                level = key + "."
                self.read_dict(value, level)
            else:
                self[level + key] = value

    def register_adapters(self, adapters):
        for name, adapter in adapters.items():
            self._adapter[name] = adapter

    def get_adapter(self, key):
        name = self.resolve_name(key, self.adapter_prefix)
        return self._adapter.get(name)

    def register_converters(self, converters, name=None):
        for name, converter in converters.items():
            self._converter[name] = converter

    def get_converter(self, key):
        name = self.resolve_name(key, self.converter_prefix)
        return self._converter.get(name)

    def resolve_name(self, key, prefix=""):
        if key.startswith("."):
            return "dot"
        key_parts = [prefix] + key.split(".")
        keys = []
        if len(key_parts) > 2:
            keys.append(".".join(key_parts[:-1]) + ".")
        keys.append(".".join(key_parts))
        print(keys)
        names = ["default"]
        for k in keys:
            names = self._data.get(k, names)
        return str(names[-1])

    def __str__(self):
        data = {key: self[key] for key in self if not key.startswith(".")}
        return pformat(data)


def main():
    data = """
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

    cfg = Config()
    cfg.read_data(data)
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


if __name__ == "__main__":
    main()
