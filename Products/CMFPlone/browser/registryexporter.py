# -*- coding: utf-8 -*-
from plone.registry.interfaces import IRegistry
from Products.Five import BrowserView
from zope.component import getUtility
from lxml import etree


class RegistryExporterView(BrowserView):
    """this view make sane exports of the registry.

    Main goal is to export in a way, that the output can be reused as
    best practive settings
    """

    def __call__(self):
        selected_prefix = self.request.form.get('prefix', None)
        if not selected_prefix:
            return "prefix GET parameter needed"
        registry = getUtility(IRegistry)
        xmlreg = etree.Element('registry')
        xmlrecords = etree.SubElement(xmlreg, 'records')
        for regkey in registry.records.keys():
            prefix, key = regkey.rsplit('.', 1)
            if selected_prefix != prefix:
                continue
            record = registry.records[regkey]
            if prefix not in xmlrecords.attrib:
                xmlrecords.attrib['prefix'] = prefix
                xmlrecords.attrib['interface'] = record.interfaceName

            # look at plone.supermodel.utils.valueToElement
            xmlvalue = etree.SubElement(xmlrecords, 'value')
            xmlvalue.attrib['key'] = record.fieldName
            if isinstance(record.value, basestring):
                xmlvalue.text = record.value
            elif isinstance(record.value, (list, tuple)):
                for element in record.value:
                    xmlel = etree.SubElement(xmlvalue, 'element')
                    xmlel.text = element
            elif isinstance(record.value, bool):
                xmlvalue.text = 'True' if record.value else 'False'
        self.request.response.setHeader('Content-Type', 'text/xml')
        return etree.tostring(xmlreg, pretty_print=True)
