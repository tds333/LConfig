# lconfig parsing and more
import os
import string
from pprint import pformat
from collections import OrderedDict
from collections.abc import MutableMapping, Mapping
from json import dumps, loads
import inspect
from typing import List, Dict, Iterable, Optional, Callable, Any, Iterator, Union

__all__ = ["LConfig", "LConfigProxy", "Adapter", "Converter"]

_KEY_CHARS = string.ascii_lowercase
_KEY_CHARS += string.digits
_KEY_CHARS += "." + "_"

# typing
AdapterFunction = Callable[[str, Any, List[str], "LConfig"], List[str]]
ConverterFunction = Callable[[str, List[str], "LConfig"], Any]


def make_prefix(prefix: str, key: str = ""):
    if prefix and not prefix.endswith("."):
        return f"{prefix}.{key}"
    return f"{prefix}{key}"


class Parser:

    def read_file(self, lconfig: "LConfig", filename, prefix: str = ""):
        filename = os.fspath(filename)
        with open(filename, mode="r", encoding="utf8") as config_file:
            self.read_data(lconfig, config_file, prefix)
        return self

    def read_data(self, lconfig: "LConfig", data: Any, prefix: str = ""):
        pass


class StrictParser(Parser):

    ASSIGN_CHAR = "="

    def read_data(self, lconfig, data: Union[Iterable, str], prefix: str = ""):
        if isinstance(data, str):
            data = data.splitlines()
        for number, line in enumerate(data):
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            key, _, value = line.partition(self.ASSIGN_CHAR)
            if _ != self.ASSIGN_CHAR:
                raise ValueError(
                    "Invalid format in line %d: %r."
                    " No %r found to asign a value." % (number, line, self.ASSIGN_CHAR)
                )
            orig_key = key
            key = key.strip()
            if not key:
                raise KeyError(
                    "Invalid or empty key %r in line %d: %r." % (orig_key, number, line)
                )
            value = value.strip()
            key = make_prefix(prefix, key)
            try:
                lconfig[key] = value
            except ValueError as ex:
                raise ValueError("In line %d: %r.\nError: %s" % (number, line, ex))
        return self


class Adapter:

    @staticmethod
    def raw(key: str, value: Any, values: List[str], config: "LConfig"):
        values.append(str(value))
        return values

    @staticmethod
    def overwrite(key, value, values, config):
        return [str(value)]

    @staticmethod
    def append(key, value, values, config):
        """
        Append new value if it is not empty.
        """
        if value:
            values.append(str(value))
        return values

    @staticmethod
    def concat(key, value, values, config):
        """
        Concatenate new values to existing in one value.
        """
        if value:
            if not values:
                values.append(str(value))
            else:
                values[0] += str(value)
        return values

    @staticmethod
    def append_default(key, value, values, config):
        """
        Append new value. Empty value resets to default
        """
        if value:
            values.append(str(value))
        else:  # empty value resets to default
            values = [config.resolve_name(key, prefix=config._DEFAULT_PREFIX, default="")]
        return values

    @staticmethod
    def append_delete(key, value, values, config):
        """
        Append new value. Empty value deletes key
        """
        if value:
            values.append(str(value))
        else:
            return []  # empty value deletes key
        return values

    @staticmethod
    def append_remove(key, value, values, config):
        """
        Append new value. Empty value removes last value
        """
        if value:
            values.append(str(value))
        elif values:
            values.pop()
        return values

    @staticmethod
    def listing(key, value, values, config):
        new_values = str(value).split(",")
        if new_values:
            values.extend(v.strip() for v in new_values if v.strip())
        return values

    @staticmethod
    def json(key, value, values, config):
        """
        Adapt value to a Json string and append it.
        """
        if isinstance(value, str):
            jvalue = value
        else:
            jvalue = dumps(value)
        if jvalue:
            values.append(jvalue)
        return values

    default = append
    dot = overwrite


class Interpolate(string.Template):

    idpattern = r"(?-i:[\._a-z0-9][\._a-z0-9]*)"


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
    def string(key: str, values: List[str], config: "LConfig"):
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

    @staticmethod
    def json(key: str, values: List[str], config: "LConfig"):
        return loads(values[-1])

    @staticmethod
    def stringjoin(key, values, config):
        return "\n".join(values)

    default = string
    dot = string


class LConfig(MutableMapping):

    PARSER = StrictParser
    ADAPTER = Adapter
    CONVERTER = Converter

    _KEY_CHARS = frozenset(_KEY_CHARS)
    _ADAPTER_PREFIX = ".adapt"
    _CONVERTER_PREFIX = ".convert"
    _DEFAULT_PREFIX = ".default"

    def __init__(self):
        self._data: Dict[str, List[str]] = OrderedDict()
        self._adapter: Dict[str, Callable] = {}
        self._converter: Dict[str, Callable] = {}
        adapters = dict(inspect.getmembers(self.ADAPTER, inspect.isfunction))
        converters = dict(inspect.getmembers(self.CONVERTER, inspect.isfunction))
        self.register_adapters(adapters)
        self.register_converters(converters)
        self._parser = self.PARSER()

    @classmethod
    def adapt_key(cls, key: str) -> str:
        key = str(key)
        not_allowed_chars = set(key) - cls._KEY_CHARS
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
        try:
            values = self._data[key]
        except KeyError:
            if key.endswith("."):
                return LConfigProxy(self, key)
            raise KeyError("Key %r not found in %r." % (key, self.__class__.__name__))
        converter = self.get_converter(key)
        if converter is not None:
            return converter(key, values, self)
        return values

    def __setitem__(self, key: str, value: Any):
        values: List[str]
        key = self.adapt_key(key)
        values = self._data.get(key, [])
        adapter = self.get_adapter(key)
        if adapter is not None:
            values = adapter(key, value, values, self)
        else:
            values.append(str(value))
        if values:
            self._data[key] = values
        elif key in self._data:
            del self._data[key]

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

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
        elif name in self:
            self[name] = value
        else:
            raise AttributeError("Attribute %r not found." % name)

    def __contains__(self: "LConfig", key: str) -> bool:
        return key in self._data

    def read_dict(self, data: Mapping, prefix: str = ""):
        for key in data:
            value = data[key]
            prefix_key = make_prefix(prefix, key)
            if isinstance(value, str):
                self[prefix_key] = value
            elif isinstance(value, Mapping):
                self.read_dict(value, prefix_key)
            else:
                self._data[prefix_key] = [str(v) for v in value]
        return self

    def read_data(self, data: Union[Iterable, str], prefix: str = ""):
        self._parser.read_data(self, data, prefix)
        return self

    def read_file(self, filename, prefix: str = ""):
        self._parser.read_file(self, filename, prefix)
        return self

    def write_data(self, data, key_filter: Optional[callable] = None):
        key_filter = lambda key: True if key_filter is None else key_filter
        for key in self:
            if key_filter(key):
                values = self.get_raw(key)
                for value in values:
                    data.write("{key} = {value}\n".format(key=key, value=value))

    def write_file(self, filename, key_filter=None):
        filename = os.fspath(filename)
        with open(filename, mode="w", encoding="utf8") as config_file:
            self.write_data(config_file, key_filter)

    def register_adapters(self, adapters: Mapping):
        for name, adapter in adapters.items():
            self._adapter[name] = adapter

    def get_adapter(
        self, key: str, default: str = "default"
    ) -> Optional[AdapterFunction]:
        name = self.resolve_name(key, self._ADAPTER_PREFIX, default)
        return self._adapter.get(name)

    def adapter_names(self):
        return list(iter(self._adapter))

    def register_converters(self, converters):
        for name, converter in converters.items():
            self._converter[name] = converter

    def get_converter(
        self, key: str, default: str = "default"
    ) -> Optional[ConverterFunction]:
        name = self.resolve_name(key, self._CONVERTER_PREFIX, default)
        return self._converter.get(name)

    def converter_names(self) -> List[str]:
        return list(iter(self._converter))

    def resolve_name(self, key: str, prefix: str = "", default: Optional[str] = None):
        if key.startswith("."):
            return "dot"
        elif key == "":
            return default
        key_parts = [prefix] + key.split(".")
        search_key = f"{prefix}.{key}"
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
        self._prefix = make_prefix(prefix)

    def __getitem__(self, key: str):
        return self._config[self._prefix + key]

    def __setitem__(self, key: str, value: str):
        key = self._prefix + LConfig.adapt_key(key)
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

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
        elif name in self:
            self[name] = value
        else:
            raise AttributeError("Attribute %r not found." % name)

    def __contains__(self, key: str) -> bool:
        key = self._prefix + key
        return key in self._config

    def read_data(self, data):
        return self._config.read_data(data, self._prefix)

    def read_dict(self, data):
        return self._config.read_dict(data, self._prefix)

    def read_file(self, filename):
        return self._config.read_file(filename, self._prefix)

    def get_config(self) -> LConfig:
        return self._config

    def get_prefix(self) -> str:
        return self._prefix


class TolerantParser(Parser):
    """
    Keys are converted to lower case.
    For multi assignement the key is optional and last one is used.
    """

    ASSIGN_CHAR = "="

    def read_data(self, lconfig, data: Iterable, prefix: str = ""):
        if isinstance(data, str):
            data = data.splitlines()
        last_key = ""
        for number, line in enumerate(data):
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            key, _, value = line.partition(self.ASSIGN_CHAR)
            if _ != self.ASSIGN_CHAR:
                raise ValueError(
                    "Invalid format in line %d: %r."
                    " No %r found to asign a value." % (number, line, self.ASSIGN_CHAR)
                )
            key = key.strip().lower()
            value = value.strip()
            if key:  # allows empty key be same as last key
                key = make_prefix(prefix, key)
                last_key = key
            else:
                key = last_key
            try:
                lconfig[key] = value
            except ValueError as ex:
                raise ValueError("In line %d: %r.\nError: %s" % (number, line, ex))
        return self


class SimpleIniParser(Parser):

    """
    Keys are converted to lower case.
    Sections with [] set the prefix for the following keys.
    """

    def read_data(self, lconfig, data: Union[Iterable, str], prefix: str = ""):
        if isinstance(data, str):
            data = data.splitlines()
        last_key = ""
        known_keys = set()
        for number, line in enumerate(data):
            # handle comment and empty lines
            if line.startswith("#") or line.startswith(";") or not line.strip():
                continue
            # handle sections
            if line.startswith("[") and line.endswith("]"):
                prefix = line[1:-1].strip().lower()
                continue
            # handle multi line values
            if line.startswith(" ") or line.startswith("\t"):
                if not last_key:
                    raise ValueError("No key to assign the value.")
                key = last_key
                value = line
            else:
                key, _, value = line.partition("=")
                if _ != "=":
                    key, _, value = line.partition(":")
                if _ not in {"=", ":"}:
                    raise ValueError(
                        "Invalid format in line %d: %r."
                        " No assignement ('=' or  ':') found "
                        "or wrong multiline value." % (number, line, self.ASSIGN_CHAR)
                    )
                key = key.strip().lower()
                key = make_prefix(prefix, key)
                last_key = key
                if key in known_keys:
                    raise KeyError("Line %d: Key %r already set. Duplicate?" % (number, key))
                else:
                    known_keys.add(key)
            value = value.strip()
            try:
                lconfig[key] = value
            except ValueError as ex:
                raise ValueError("In line %d: %r.\nError: %s" % (number, line, ex))
        return self
