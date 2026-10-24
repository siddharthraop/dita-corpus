<?xml version="1.0" encoding="UTF-8"?>
<!--
  House rules the DITA grammar can't express. Run by tools/validate.py with lxml.isoschematron.
  role="error" fails the build; role="warning" is reported on the dashboard but does not fail it.
  XPath 1.0 (lxml's XSLT 1.0 engine), no namespaces: DITA elements are in no namespace.
-->
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt">
  <title>dita-corpus house rules</title>

  <pattern id="structure">
    <rule context="/concept | /reference | /task | /topic">
      <assert id="SD-1" role="error" test="shortdesc and normalize-space(shortdesc) != ''">Every topic needs a short
        description: search results, link previews and RAG chunks all use it.</assert>
      <assert id="LIC-1" role="error" test="prolog/data[@name='licence'] or prolog/data[@name='generated']">Adapted
        content must carry its licence and "modified" notice (CC BY 4.0 attribution).</assert>
    </rule>
  </pattern>

  <pattern id="accessibility">
    <rule context="image">
      <assert id="IMG-1" role="error" test="alt and normalize-space(alt) != ''">Images need alternative text.</assert>
    </rule>
    <rule context="object">
      <assert id="OBJ-1" role="error" test="desc and normalize-space(desc) != ''">Embedded media needs a description
        for readers who can't play it.</assert>
      <assert id="OBJ-2" role="error" test="@type">Embedded media needs a MIME type, for example video/mp4.</assert>
    </rule>
  </pattern>

  <pattern id="single-source">
    <!-- AlignR's rule: a value in a specification table comes from a key, never typed in. -->
    <rule context="table[@outputclass='spec']/tgroup/tbody/row/entry[position() &gt; 1]">
      <assert id="SPEC-1" role="error"
        test="keyword[@keyref] or translate(normalize-space(.), '0123456789', '') = normalize-space(.)">A number in a
        specification table must be a key reference (keyword keyref), so it can be changed in one place.</assert>
    </rule>
    <!-- Numbers with hardware units typed into prose are a drift risk. Warn, don't fail: a few are deliberate (KI-2).
         The rule fires on the block element and tests its own text nodes (the Schematron skeleton visits elements, not text). -->
    <rule context="p | li | dd | note">
      <let name="typed" value="text()[contains(., 'TB/s') or contains(., 'GBps') or contains(., 'GiB') or contains(., 'TFLOPs') or contains(., 'Gbps')][translate(., '0123456789', '') != .]"/>
      <report id="SPEC-2" role="warning" test="$typed">A number with a hardware unit is typed into prose instead of
        coming from a key: "<value-of select="normalize-space($typed[1])"/>"</report>
    </rule>
  </pattern>

  <pattern id="evidence">
    <rule context="/*[prolog/data[@name='model-version']]">
      <assert id="EV-1" role="error" test="prolog/critdates/revised/@modified">Evidence topics need a revised date,
        so AEGIS can tell current evidence from stale.</assert>
      <assert id="EV-2" role="error" test="prolog/data[@name='source']/@href">Evidence topics need a link to the
        source they were adapted from.</assert>
    </rule>
    <rule context="/reference[starts-with(@id, 'aia-') or starts-with(@id, 'nist-')]">
      <assert id="REQ-1" role="error" test="prolog/data[@name='requirement-id']/@value">Requirement topics need a
        requirement ID, for example aia.xi-1a.</assert>
    </rule>
  </pattern>
</schema>
