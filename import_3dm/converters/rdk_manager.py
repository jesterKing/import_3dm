import rhino3dm as r3d
import xml.etree.ElementTree as ET

class RdkManager():
  def __init__(self, document : r3d.File3dm) -> None:
    self.doc = document
    self.rdkxml = ET.fromstring(self.doc.RdkXml())
    self.mgr = self.rdkxml.find("render-content-manager-document")
    self.materials_xml = self.mgr.find("material-section")
    self.environments_xml = self.mgr.find("environment-section")
    self.textures_xml = self.mgr.find("texture-section")

  def get_materials(self):
    materials = []
    for material in self.materials_xml.findall("material"):
      rm = r3d.RenderMaterial()
      rm.SetXML(ET.tostring(material, encoding="utf-8").decode())
      materials.append(rm)
    return materials

