# lconfig parsing and more
import os
import string
from pprint import pformat
from collections import OrderedDict
from collections.abc import MutableMapping, Mapping
import inspect
from typing import List, Dict, Iterable, Optional, Callable, Any, Iterator

__all__ = ["LConfig", "LConfigProxy", "Adapter", "Converter"]

_KEY_CHARS = string.ascii_lowercase
_KEY_CHARS += string.digits
_KEY_CHARS += "." + "_"

# typing
AdapterFunction = Callable[[str, List[str], "LConfig"], Optional[List[str]]]
ConverterFunction = Callable[[str, List[str], "LConfig"], Any]


class LConfig(MutableMapping):

    KEY_CHARS = frozenset(_KEY_CHARS)
    _adapter_prefix = ".adapt"
    _converter_prefix = ".convert"
    _default_prefix = ".default"

    def __init__(self):
        self._data: Dict[str, List[str]] = OrderedDict()
        self._adapter: Dict[str, Callable] = {}
        self._converter: Dict[str, Callable] = {}
        adapters = dict(inspect.getmembers(Adapter, inspect.isfunction))
        converters = dict(inspect.getmembers(Converter, inspect.isfunction))
        self.register_adapters(adapters)
        self.register_converters(converters)

    @classmethod
    def adapt_key(cls, key: str) -> str:
        key = str(key).strip()
        not_allowed_chars = set(key) - cls.KEY_CHARS
        if not_allowed_chars:
            raise ValueError(
                "Detected not allowed character(s): %r in key %r."
                % ("".join(not_allowed_chars), key)
            )
        return key

    def get_raw(self, key: str) -> List[str]:
        return self._data[key]

    def set_raw(self, key: str, values: List[str]) -> None:
        self._data[key] = values

    def __getitem__(self, key: str):
        key = str(key).strip()
        try:
            values = self._data[key]
        except KeyError as ex:
            raise KeyError("Key %r not found in %r." % (key, self.__class__.__name__))
        converter = self.get_converter(key)
        if converter is not None:
            return converter(key, values, self)
        return values

    def __setitem__(self, key: str, value: str):
        values: Optional[List[str]]
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
        elif values is None:
            del self._data[key]
        else:  # False/empty values reset to default
            self._data[key] = self.get_default(key)

    def __delitem__(self, key: str):
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
                return LConfigProxy(config=self, prefix=dotname)
        raise AttributeError("Config key %r not found." % name)

    def __contains__(self, key) -> bool:
        key = str(key).strip()
        return key in self._data

    def read_data(self, data: Iterable, prefix: str = ""):
        last_key = ""
        for line in data:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            key, _, value = line.partition("=")
            if key:  # allows empty key be same as last key
                key = prefix + key
                last_key = key
            else:
                key = last_key
            self[key] = value

    def read_dict(self, data: Mapping, prefix: str = ""):
        for key in data:
            value = data[key]
            if isinstance(value, str):
                self[prefix + key] = value
            elif isinstance(value, Mapping):
                prefix = key + "."
                self.read_dict(value, prefix)
            else:
                self._data[prefix + key] = [str(v).strip() for v in value]

    def read_file(self, filename, prefix: str = ""):
        filename = os.fspath(filename)
        with open(filename, mode="r", encoding="utf8") as config_file:
            self.read_data(config_file, prefix)

    def write_data(self, data, dot: bool = False):
        for key in self:
            if not dot and key.startswith("."):
                continue
            values = self.get_raw(key)
            for value in values:
                data.write("{key} = {value}\n".format(key=key, value=value))

    def write_file(self, filename, dot=False):
        filename = os.fspath(filename)
        with open(filename, mode="w", encoding="utf8") as config_file:
            self.write_data(config_file, dot)

    def get_default(self, key: str, default: str = "") -> str:
        value = self.resolve_name(key, self._default_prefix, default)
        return value

    def register_adapters(self, adapters: Mapping):
        for name, adapter in adapters.items():
            self._adapter[name] = adapter

    def get_adapter(
        self, key: str, default: str = "default"
    ) -> Optional[AdapterFunction]:
        name = self.resolve_name(key, self._adapter_prefix, default)
        return self._adapter.get(name)

    def adapter_names(self):
        return list(iter(self._adapter))

    def register_converters(self, converters):
        for name, converter in converters.items():
            self._converter[name] = converter

    def get_converter(
        self, key: str, default: str = "default"
    ) -> Optional[ConverterFunction]:
        name = self.resolve_name(key, self._converter_prefix, default)
        return self._converter.get(name)

    def converter_names(self) -> List[str]:
        return list(iter(self._converter))

    def resolve_name(self, key: str, prefix: str = "", default: Optional[str] = None):
        if key.startswith("."):
            return "dot"
        elif key == "":
            return default
        key_parts = [prefix] + key.split(".")
        search_key = prefix + "." + key
        while key_parts:
            if search_key in self._data:
                return str(self._data[search_key][-1])
            if not key_parts:
                break
            key_parts.pop()
            search_key = ".".join(key_parts) + "."
        return default

    def __str__(self) -> str:
        data = {key: self[key] for key in self if not key.startswith(".")}
        return pformat(data)


class LConfigProxy(MutableMapping):

    def __init__(self, config: "LConfig", prefix: str = "") -> None:
        self._config = config
        if prefix and not prefix.endswith("."):
            prefix = prefix + "."
        self._prefix = prefix

    def __getitem__(self, key: str):
        return self._config[self._prefix + key]

    def __setitem__(self, key: str, value: str):
        key = self._prefix + key
        self._config[key] = value

    def __delitem__(self, key: str):
        key = self._prefix + key
        del self._config[key]

    def __iter__(self) -> Iterator[str]:
        prefix_len = len(self._prefix)
        for key in self._config:
            if key.startswith(self._prefix):
                yield key[prefix_len:]

    def __len__(self) -> int:
        return len(list(iter(self)))

    def __getattr__(self, name: str) -> Any:
        return self._config.__getattr__(self._prefix + name)

    def __contains__(self, key: Any) -> bool:
        key = self._prefix + str(key).strip()
        return key in self._config

    def read_data(self, data):
        self._config.read_data(data, self._prefix)

    def read_dict(self, data):
        self._config.read_dict(data, self._prefix)

    def read_file(self, filename):
        self._config.read_file(filename, self._prefix)

    def get_config(self) -> LConfig:
        return self._config

    def get_prefix(self) -> str:
        return self._prefix


class Interpolate(string.Template):

    idpattern = r"(?-i:[\._a-z0-9][\._a-z0-9]*)"


class Adapter:

    @staticmethod
    def raw(key: str, values: List[str], config: LConfig):
        return values

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
    def append_remove(key, values, config):
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
    def string(key: str, values: List[str], config: LConfig):
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
        value = str(values[-1])
        if "$" in value:
            value = Interpolate(value).substitute(config)
        return value

    default = string
    dot = string
