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

class Interpolate(string.Template):

    idpattern = r'(?-i:[\.a-zA-Z][\.a-zA-Z0-9]*)'


class Adapter:

    @staticmethod
    def append(key, values, config):
        value = values.pop()
        if value:
            values.append(value)
        return values
    
    @staticmethod
    def overwrite(key, values, config):
        return [values[-1]]

    @staticmethod
    def append_reset(key, values, config):
        value = values.pop()
        if value:
            values.append(value)
        else:
            return None  # empty value deletes key
        return values

    @staticmethod
    def listing(key, values, config):
        value = values.pop()
        new_values = value.split(",")
        if new_values:
            values.extend(v.strip() for v in new_values if v.strip())
        return values

    default = append
    dot = overwrite


class Converter:

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
    def string(key, values, config):
        return str(values[-1])

    @staticmethod
    def raw(key, values, config):
        return values

    @staticmethod
    def boolean(key, values, config):
        last_value = values[-1].lower()
        return Converter.BOOLEAN_STATES.get(last_value, False)

    @staticmethod
    def integer(key, values, config):
        return int(values[-1])

    @staticmethod
    def real(key, values, config):
        return float(values[-1])

    @staticmethod
    def stringlist(key, values, config):
        return [str(v) for v in values]

    @staticmethod
    def intlist(key, values, config):
        return [int(v) for v in values]

    @staticmethod
    def interpolate(key, values, config):
        # one level interpolation
        value = str(values[-1])
        if "$" in value:
            value = Interpolate(value).substitute(config)
        return value

    default = string
    dot = string


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
        adapters = dict(inspect.getmembers(Adapter, inspect.isfunction))
        converters = dict(inspect.getmembers(Converter, inspect.isfunction))
        self.register_adapters(adapters)
        self.register_converters(converters)

    @classmethod
    def adapt_key(cls, key):
        key = str(key).strip()
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
        key = str(key).strip()
        try:
            values = self._data[key]
        except KeyError as ex:
            raise KeyError("Key %r not found in %r." % (key, self.__class__.__name__))
        converter = self.get_converter(key)
        if converter is not None:
            return converter(key, values, self)
        return values

    def __setitem__(self, key, value):
        key = self.adapt_key(key)
        if key in self._data:
            values = self._data[key]
        else:
            values = []
        values.append(str(value).strip())
        adapter = self.get_adapter(key)
        if adapter is not None:
            values = adapter(key, values, self)
        if values:
            self._data[key] = values
        else:
            del self._data[key]

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
        # prefix_key = ".".join(key_parts)
        # dot_key = ".".join(key_parts[:-1]) + "."
        if len(key_parts) > 2:
            keys.append(".".join(key_parts[:-1]) + ".")
        keys.append(".".join(key_parts))
        names = ["default"]
        for k in keys:
            names = self._data.get(k, names)
        return str(names[-1])

    def __str__(self):
        data = {key: self[key] for key in self if not key.startswith(".")}
        return pformat(data)


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
        part_len = len(self._part)
        for key in self._config:
            if key.startswith(self._part):
                yield key[part_len:]

    def __len__(self):
        return len(list(iter(self)))
        # return len(self._config)

    def __getattr__(self, name):
        return self._config.__getattr__(self._part + name)
