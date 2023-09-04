from ..export_params import ExportParams
from .base_entity import BaseEntity
import os
import json

class MaterialEntity(BaseEntity):

    def __init__(self, obj):
        super().__init__(obj)
        
    def santitize_image_name(self, image, output_dir):
        
        os.makedirs(output_dir + "/textures/", exist_ok=True)
        
        image.name = image.name.replace(".png","")+".png"
        last3chars = image.name[len(image.name)-3:len(image.name)]
        
        # blender will append ".001" on an object name if it's name clashes with another. We want .png at the end.
        # to combat this, we detect the .001 at the end (any number), then put it inside the name and append .png at the end.
        if last3chars.isdigit() and image.name[len(image.name)-4:len(image.name)-3] == ".":
            image.name = image.name[0:len(image.name)-3].replace(".png","")+last3chars+".png"
        
        originalpath = image.filepath
        image.save(filepath=output_dir+"/textures/"+image.name)
        
        image.filepath = originalpath
        
        return "textures/"+image.name

    def generate(self, output_dir = ""):
        mat = self.obj
            
        #this is default data, as a reference to where I should shove things - @989onan
        matdata = {
            "materialVersion": 1,
            "materials": [
                {
                    "albedo": [
                        1,
                        1,
                        1
                    ],
                    "emissive": [
                        0,
                        0,
                        0
                    ],
                    "scattering": 0,
                    "cullFaceMode": "CULL_BACK"
                }
            ]
        }
        if not mat.use_nodes or not mat.node_tree:
            return ""
        tree = mat.node_tree
        nodes = tree.nodes
        
        output = None
        #find an output node with a principled going into it.
        for n in nodes:
            if n.type == 'OUTPUT_MATERIAL':
                if len(n.inputs["Surface"].links) > 0:
                    if n.inputs["Surface"].links[0].from_node:
                        if n.inputs["Surface"].links[0].from_node.type == "BSDF_PRINCIPLED":
                            output = n
                            break
        
        if not output:
            return ""
        
        principled = output.inputs["Surface"].links[0].from_node
        matdata["materials"][0]["albedo"] = principled.inputs['Base Color'].default_value[:3]
        matdata["materials"][0]["opacity"] = principled.inputs['Alpha'].default_value
        matdata["materials"][0]["metallic"] = principled.inputs['Metallic'].default_value
        matdata["materials"][0]["roughness"] = principled.inputs['Roughness'].default_value
        matdata["materials"][0]["emissive"] = principled.inputs['Emission'].default_value[:3]
        
        try: 
            base_color_source = principled.inputs["Base Color"].links[0].from_node
            if base_color_source.type == "TEX_IMAGE":
                matdata["materials"][0]["albedoMap"] = self.santitize_image_name(base_color_source.image, output_dir)
        except Exception as e:
            print(e)
        
        try: 
            base_color_source = principled.inputs["Alpha"].links[0].from_node
            if base_color_source.type == "TEX_IMAGE":
                matdata["materials"][0]["opacityMap"] = self.santitize_image_name(base_color_source.image, output_dir)
        except:
            pass
        
        try: 
            base_color_source = principled.inputs["Emission"].links[0].from_node
            if base_color_source.type == "TEX_IMAGE":
                matdata["materials"][0]["emissiveMap"] = self.santitize_image_name(base_color_source.image, output_dir)
        except:
            pass
        
        try: 
            base_color_source = principled.inputs["Roughness"].links[0].from_node
            if base_color_source.type == "TEX_IMAGE":
                matdata["materials"][0]["roughnessMap"] = self.santitize_image_name(base_color_source.image, output_dir)
            elif base_color_source.type == "INVERT":
                matdata["materials"][0]["glossMap"] = self.santitize_image_name(base_color_source.links[1].from_node.image, output_dir)
        except:
            pass
        
        try: 
            metallic_color_source = None
            specular_color_source = None
            try:
                metallic_color_source = principled.inputs["Metallic"].links[0].from_node
            except:
                pass
            try:
                specular_color_source = principled.inputs["Specular"].links[0].from_node
            except:
                pass
            
            if metallic_color_source:
                if metallic_color_source.type == "TEX_IMAGE":
                    matdata["materials"][0]["metallicMap"] = self.santitize_image_name(metallic_color_source.image, output_dir)
                    specular_color_source = None
            if specular_color_source:
                if specular_color_source.type == "TEX_IMAGE":
                    matdata["materials"][0]["specularMap"] = self.santitize_image_name(specular_color_source.image, output_dir)
        except:
            pass
        
        try: 
            normal_data_type = principled.inputs["Normal"].links[0].from_node
            if normal_data_type.type == "NORMAL_MAP":
                matdata["materials"][0]["normalMap"] = self.santitize_image_name(normal_data_type.links[1].from_node.image, output_dir)
            elif normal_data_type.type == "BUMP":
                matdata["materials"][0]["bumpMap"] = self.santitize_image_name(normal_data_type.links[2].from_node.image, output_dir)
        except:
            pass
            
        lightmapped_image_node = None
        for n in nodes:
            if n.type == 'OUTPUT_AOV':
                if n.name == "Lightmap":
                    if len(n.inputs["Color"].links) > 0:
                        if n.inputs["Color"].links[0].from_node:
                            if n.inputs["Color"].links[0].from_node.type == "TEX_IMAGE":
                                lightmapped_image_node = n.inputs["Color"].links[0].from_node
                                break
        if lightmapped_image_node:
            matdata["materials"][0]["lightMap"] = self.santitize_image_name(lightmapped_image_node.image, output_dir)
        
        self.obj.overte.material_data = json.dumps(matdata)
        

    def get_material(self):
        material = {}
        
        if self.obj.overte.material_data != '':
            material["materialData"] = json.loads(self.obj.overte.material_data)
            self.obj.overte.material_data = ''
            
        
        if self.obj.overte.material_url != '':
            materialData = ExportParams.get_url(self.obj.overte.material_url)
            if self.obj.overte.material_url == 'materialData':
                materialData = self.obj.overte.material_url
            material["materialURL"] = materialData
        
        if self.obj.overte.material_priority != 0:
            material["priority"] = self.obj.overte.material_priority

        if self.obj.overte.material_mapping_mode != 'default':
            material["materialMappingMode"] = self.obj.overte.material_mapping_mode

        if sum(self.obj.overte.material_position) > 0.0:
            material["materialMappingPos"] = {
                "x": self.obj.overte.material_position[0],
                "y": self.obj.overte.material_position[1],
            }

        scale = self.obj.overte.material_scale
        if scale[0] != 1.0 or scale[1] != 1.0:
            material["materialMappingScale"] = {
                "x": scale[0],
                "y": scale[1],
            }

        if self.obj.overte.material_rotation != 0.0:
            material["materialMappingRot"] = self.obj.overte.material_rotation

        if self.obj.overte.material_repeat != True:
            material["materialRepeat"] = self.obj.overte.material_repeat

        return material

    def export(self, parentEntity):
        entity = super().export("Material")
        material = self.get_material()

        materialEntity = {
            "name": parentEntity["name"] + '.' + entity["name"],
            "position": { "x": 0, "y": 0, "z": 0 },
            "rotation": { "x": 0, "y": 0, "z": 0, "w": 1 },
            "queryAACube": parentEntity["queryAACube"],
            "parentID": parentEntity["id"]
        }
        return {**entity, **materialEntity, **material}

    def draw_panel(self, layout):
        box = layout.box()
        row = box.row()
        row.prop(self.obj.overte, "material_url")
        row = box.row()
        row.prop(self.obj.overte, "material_data")
        row = box.row()
        row.prop(self.obj.overte, "material_priority")
        row = box.row()
        row.prop(self.obj.overte, "material_mapping_mode")
        row = box.row()
        row.prop(self.obj.overte, "material_position")
        row = box.row()
        row.prop(self.obj.overte, "material_scale")
        row = box.row()
        row.prop(self.obj.overte, "material_rotation")
        row = box.row()
        row.prop(self.obj.overte, "material_repeat")

        self.draw_entity_panel(layout)
        self.draw_behavior_panel(layout)
        self.draw_script_panel(layout)
        self.draw_physics_panel(layout)
