# XML documentation and schemas

Official resources downloaded on 2026-09-23. Original downloads are preserved unchanged. The EASA schema was also extracted from its ZIP for direct use.

## EASA

[Publisher documentation page](https://www.easa.europa.eu/en/easy-access-rules-xml-export)

| Local file | Purpose | Official source |
|---|---|---|
| [Export guide](easa-xml-export-guide.pdf) | Package structure, metadata fields, links between metadata and content, processing guidance | [Download](https://www.easa.europa.eu/en/downloads/136656/en) |
| [EASA XSD](easa-schema/EASA-eRules-XML-Export-Schema-1.0.0.xsd) | Schema for the EASA metadata namespace, version 1.0.0 | [Original ZIP](https://www.easa.europa.eu/en/downloads/136696/en) |
| [XSLT examples](easa-xslt-examples.zip) | Official example transformations, including CSV, JSON, filtering and splitting | [Download](https://www.easa.europa.eu/en/downloads/137730/en) |

The website also offers [HTML schema documentation](https://www.easa.europa.eu/en/downloads/136657/en) and [PDF schema documentation](https://www.easa.europa.eu/en/downloads/136695/en), not downloaded here.

The downloaded Air Operations XML is a Flat OPC package containing two relevant layers:

1. EASA metadata in namespace `http://www.easa.europa.eu/erules-export`: `document`, `toc`, `heading` and `topic`. Topics expose `ERulesId`, `source-title`, `TypeOfContent`, `RegulatorySource`, dates and `ParentIR`, among other fields. Some attributes are empty.
2. Actual paragraphs and tables in the package's `/word/document.xml`, using WordprocessingML namespace `http://schemas.openxmlformats.org/wordprocessingml/2006/main`.

Find the EASA `document` by namespace rather than hardcoding `/customXml/item9.xml`: the guide states that the custom XML item number varies. Join `topic/@sdt-id` to `w:sdt/w:sdtPr/w:id/@w:val`, then read its `w:sdtContent` in document order. Preserve paragraph text, table headers/merged cells, hyperlinks and bookmarks.

Use **ERulesId** to identify topics across files/versions. The guide explicitly says **sdt-id is only a within-file pointer** and may change between versions. Add source version and content hash to stored records.

The EASA XSD validates the embedded EASA metadata, not the entire WordprocessingML package. Office Open XML has separate schemas and tooling, linked in chapter 4 of the export guide. Detailed subclause interpretation and executable rule logic are outside these schemas.

Useful guide locations: package/content linkage, pages 9–11; processing and external resources, chapters 3–4; attribute descriptions, chapter 5. The example transformations have been downloaded but not executed.

## FAA / annual CFR

[Publisher CFR help](https://www.govinfo.gov/help/cfr) and [schema resources](https://www.govinfo.gov/bulkdata/CFR/resources).

| Local file | Purpose | Official source |
|---|---|---|
| [User guide](CFR-XML_User-Guide_v1.pdf) | CFR XML structure, tag descriptions, XPath examples and tables | [Download](https://www.govinfo.gov/bulkdata/CFR/resources/CFR-XML_User-Guide_v1.pdf) |
| [CFRMergedXML.xsd](CFRMergedXML.xsd) | Schema explicitly referenced by our Part 117 XML | [Download](https://www.govinfo.gov/bulkdata/CFR/resources/CFRMergedXML.xsd) |
| [cfr.xsl](cfr.xsl) | Publisher's display stylesheet, referenced by the XML | [Download](https://www.govinfo.gov/bulkdata/CFR/resources/cfr.xsl) |

Our file uses `CFRGRANULE` as its root, with `FDSYS` metadata and a `PART`. Parse `SECTION`, `SECTNO`, `SUBJECT`, `P` and `GPOTABLE` in context and preserve the original ordering and inline text. Part 117 contains 15 `SECTION` elements and Tables A–C. Avoid flattening tables into undifferentiated text.

These resources describe the annual CFR file we downloaded. eCFR XML/API resources are separate: use the [eCFR developer documentation](https://www.ecfr.gov/reader-aids/ecfr-developer-resources) if adopting that source instead; do not assume identical structure or version dates.

## Verification performed

Using `lxml.etree.XMLSchema`:

- The complete `faa-14-cfr-part-117-2026.xml` **passed** `CFRMergedXML.xsd` validation.
- The embedded EASA `document` element from `easa-air-operations-rev24-2026-03.xml` **passed** the supplied EASA XSD validation.
- Full EASA package/WordprocessingML validation was **not** performed.

These checks establish conformance to the supplied structural schemas, not completeness, legal interpretation or correct conversion into the repository's rule model.

Minimal validation pattern (Python with `lxml` installed), run from the repository root:

```python
from pathlib import Path
from lxml import etree

base = Path('references/ftl')
docs = base / 'xml-documentation'
parser = etree.XMLParser(resolve_entities=False, no_network=True)

faa_schema = etree.XMLSchema(etree.parse(str(docs / 'CFRMergedXML.xsd'), parser))
faa_schema.assertValid(etree.parse(str(base / 'faa-14-cfr-part-117-2026.xml'), parser))

easa_schema = etree.XMLSchema(etree.parse(
    str(docs / 'easa-schema/EASA-eRules-XML-Export-Schema-1.0.0.xsd'), parser
))
package = etree.parse(str(base / 'easa-air-operations-rev24-2026-03.xml'), parser)
metadata = package.find('.//{http://www.easa.europa.eu/erules-export}document')
assert metadata is not None
easa_schema.assertValid(metadata)
```
