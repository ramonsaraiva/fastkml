from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from typing_extensions import TypedDict

import fastkml.config as config
from fastkml.base import _BaseObject
from fastkml.base import _XMLObject
from fastkml.types import Element


class SimpleField(TypedDict):
    name: str
    type: str
    displayName: str  # noqa: N815


class Schema(_BaseObject):
    """
    Specifies a custom KML schema that is used to add custom data to
    KML Features.
    The "id" attribute is required and must be unique within the KML file.
    <Schema> is always a child of <Document>.
    """

    __name__ = "Schema"

    _simple_fields = None
    # The declaration of the custom fields, each of which must specify both the
    # type and the name of this field. If either the type or the name is
    # omitted, the field is ignored.
    name = None

    def __init__(
        self,
        ns: Optional[str] = None,
        id: Optional[str] = None,
        target_id: Optional[str] = None,
        name: Optional[str] = None,
        fields: None = None,
    ) -> None:
        if id is None:
            raise ValueError("Id is required for schema")
        super().__init__(ns=ns, id=id, target_id=target_id)
        self.simple_fields = fields
        self.name = name

    @property
    def simple_fields(self) -> Tuple[SimpleField, ...]:
        return tuple(
            {
                "type": simple_field["type"],
                "name": simple_field["name"],
                "displayName": simple_field.get("displayName"),
            }
            for simple_field in self._simple_fields
            if simple_field.get("type") and simple_field.get("name")
        )

    @simple_fields.setter
    def simple_fields(self, fields):
        self._simple_fields = []
        if isinstance(fields, dict):
            self.append(**fields)
        elif isinstance(fields, (list, tuple)):
            for field in fields:
                if isinstance(field, (list, tuple)):
                    self.append(*field)
                elif isinstance(field, dict):
                    self.append(**field)
        elif fields is None:
            self._simple_fields = []
        else:
            raise ValueError("Fields must be of type list, tuple or dict")

    def append(self, type: str, name: str, display_name: Optional[str] = None) -> None:
        """
        append a field.
        The declaration of the custom field, must specify both the type
        and the name of this field.
        If either the type or the name is omitted, the field is ignored.

        The type can be one of the following:
            string
            int
            uint
            short
            ushort
            float
            double
            bool

        <displayName>
        The name, if any, to be used when the field name is displayed to
        the Google Earth user. Use the [CDATA] element to escape standard
        HTML markup.
        """
        allowed_types = [
            "string",
            "int",
            "uint",
            "short",
            "ushort",
            "float",
            "double",
            "bool",
        ]
        if type not in allowed_types:
            raise TypeError(
                f"{name} has the type {type} which is invalid. "
                "The type must be one of "
                "'string', 'int', 'uint', 'short', "
                "'ushort', 'float', 'double', 'bool'"
            )
        self._simple_fields.append(
            {"type": type, "name": name, "displayName": display_name}
        )

    def from_element(self, element: Element) -> None:
        super().from_element(element)
        self.name = element.get("name")
        simple_fields = element.findall(f"{self.ns}SimpleField")
        self.simple_fields = None
        for simple_field in simple_fields:
            sfname = simple_field.get("name")
            sftype = simple_field.get("type")
            display_name = simple_field.find(f"{self.ns}displayName")
            sfdisplay_name = display_name.text if display_name is not None else None
            self.append(sftype, sfname, sfdisplay_name)

    def etree_element(self) -> Element:
        element = super().etree_element()
        if self.name:
            element.set("name", self.name)
        for simple_field in self.simple_fields:
            sf = config.etree.SubElement(element, f"{self.ns}SimpleField")
            sf.set("type", simple_field["type"])
            sf.set("name", simple_field["name"])
            if simple_field.get("displayName"):
                dn = config.etree.SubElement(sf, f"{self.ns}displayName")
                dn.text = simple_field["displayName"]
        return element


class Data(_XMLObject):
    """Represents an untyped name/value pair with optional display name."""

    __name__ = "Data"

    def __init__(
        self,
        ns: Optional[str] = None,
        name: Optional[str] = None,
        value: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> None:
        super().__init__(ns)

        self.name = name
        self.value = value
        self.display_name = display_name

    def etree_element(self) -> Element:
        element = super().etree_element()
        element.set("name", self.name)
        value = config.etree.SubElement(element, f"{self.ns}value")
        value.text = self.value
        if self.display_name:
            display_name = config.etree.SubElement(element, f"{self.ns}displayName")
            display_name.text = self.display_name
        return element

    def from_element(self, element: Element) -> None:
        super().from_element(element)
        self.name = element.get("name")
        tmp_value = element.find(f"{self.ns}value")
        if tmp_value is not None:
            self.value = tmp_value.text
        display_name = element.find(f"{self.ns}displayName")
        if display_name is not None:
            self.display_name = display_name.text


class ExtendedData(_XMLObject):
    """Represents a list of untyped name/value pairs. See docs:

    -> 'Adding Untyped Name/Value Pairs'
       https://developers.google.com/kml/documentation/extendeddata

    """

    __name__ = "ExtendedData"

    def __init__(
        self, ns: Optional[str] = None, elements: Optional[List[Data]] = None
    ) -> None:
        super().__init__(ns)
        self.elements = elements or []

    def etree_element(self) -> Element:
        element = super().etree_element()
        for subelement in self.elements:
            element.append(subelement.etree_element())
        return element

    def from_element(self, element: Element) -> None:
        super().from_element(element)
        self.elements = []
        untyped_data = element.findall(f"{self.ns}Data")
        for ud in untyped_data:
            el = Data(self.ns)
            el.from_element(ud)
            self.elements.append(el)
        typed_data = element.findall(f"{self.ns}SchemaData")
        for sd in typed_data:
            el = SchemaData(self.ns, "dummy")
            el.from_element(sd)
            self.elements.append(el)


class SchemaData(_XMLObject):
    """
    <SchemaData schemaUrl="anyURI">
    This element is used in conjunction with <Schema> to add typed
    custom data to a KML Feature. The Schema element (identified by the
    schemaUrl attribute) declares the custom data type. The actual data
    objects ("instances" of the custom data) are defined using the
    SchemaData element.
    The <schemaURL> can be a full URL, a reference to a Schema ID defined
    in an external KML file, or a reference to a Schema ID defined
    in the same KML file.
    """

    __name__ = "SchemaData"
    schema_url = None
    _data = None

    def __init__(
        self,
        ns: Optional[str] = None,
        schema_url: Optional[str] = None,
        data: None = None,
    ) -> None:
        super().__init__(ns)
        if (not isinstance(schema_url, str)) or (not schema_url):
            raise ValueError("required parameter schema_url missing")
        self.schema_url = schema_url
        self._data = []
        self.data = data

    @property
    def data(self):
        return tuple(self._data)

    @data.setter
    def data(self, data):
        if isinstance(data, (tuple, list)):
            self._data = []
            for d in data:
                if isinstance(d, (tuple, list)):
                    self.append_data(*d)
                elif isinstance(d, dict):
                    self.append_data(**d)
        elif data is None:
            self._data = []
        else:
            raise TypeError("data must be of type tuple or list")

    def append_data(self, name: str, value: Union[int, str]) -> None:
        if isinstance(name, str) and name:
            self._data.append({"name": name, "value": value})
        else:
            raise TypeError("name must be a nonempty string")

    def etree_element(self) -> Element:
        element = super().etree_element()
        element.set("schemaUrl", self.schema_url)
        for data in self.data:
            sd = config.etree.SubElement(element, f"{self.ns}SimpleData")
            sd.set("name", data["name"])
            sd.text = data["value"]
        return element

    def from_element(self, element: Element) -> None:
        super().from_element(element)
        self.data = []
        self.schema_url = element.get("schemaUrl")
        simple_data = element.findall(f"{self.ns}SimpleData")
        for sd in simple_data:
            self.append_data(sd.get("name"), sd.text)
