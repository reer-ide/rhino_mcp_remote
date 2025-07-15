import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

selected_ids = rs.SelectedObjects()
            
if not selected_ids:
    print("No object selected")
    exit()

print(f"Found {len(selected_ids)} selected object(s)")
print("=" * 50)

# Collect object data
for i, obj_id in enumerate(selected_ids):
    print(f"\nOBJECT {i + 1}:")
    print("-" * 30)
    
    # Get basic object information
    obj = sc.doc.Objects.Find(obj_id)
    if not obj:
        print("Object not found")
        continue
        
    obj_data = obj.Attributes
    geometry = obj.Geometry
    
    # Print basic object information
    print(f"Object ID: {obj_id}")
    print(f"Object Type: {type(geometry).__name__}")
    print(f"Geometry Type: {geometry.ObjectType}")
    
    # Print all attributes
    print("\nATTRIBUTES:")
    print(f"  Name: {obj_data.Name if obj_data.Name else 'None'}")
    print(f"  Layer Index: {obj_data.LayerIndex}")
    print(f"  Layer Name: {sc.doc.Layers[obj_data.LayerIndex].Name}")
    print(f"  Color Source: {obj_data.ColorSource}")
    print(f"  Object Color: {obj_data.ObjectColor}")
    print(f"  Material Index: {obj_data.MaterialIndex}")
    print(f"  Material Source: {obj_data.MaterialSource}")
    print(f"  Line Type Index: {obj_data.LinetypeIndex}")
    print(f"  Line Type Source: {obj_data.LinetypeSource}")
    print(f"  Plot Color: {obj_data.PlotColor}")
    print(f"  Plot Weight: {obj_data.PlotWeight}")
    print(f"  Plot Weight Source: {obj_data.PlotWeightSource}")
    print(f"  Display Order: {obj_data.DisplayOrder}")
    print(f"  Visible: {obj_data.Visible}")
    print(f"  Mode: {obj_data.Mode}")
    print(f"  Space: {obj_data.Space}")
    print(f"  Viewport ID: {obj_data.ViewportId}")
    
    # Print group information
    if obj_data.GroupCount > 0:
        print(f"  Group Count: {obj_data.GroupCount}")
        group_list = []
        for j in range(obj_data.GroupCount):
            group_list.append(str(obj_data.GetGroupList()[j]))
        print(f"  Groups: {', '.join(group_list)}")
    else:
        print("  Groups: None")
    
    # Print user data if available
    user_data = obj_data.UserData
    if user_data.Count > 0:
        print(f"  User Data Count: {user_data.Count}")
        for k in range(user_data.Count):
            ud = user_data[k]
            print(f"    User Data {k}: {ud.Description}")
    else:
        print("  User Data: None")
    
    # Print geometry-specific information
    print(f"\nGEOMETRY PROPERTIES:")
    print(f"  Valid: {geometry.IsValid}")
    print(f"  Deformable: {geometry.IsDeformable}")
    
    # Print bounding box
    bbox = geometry.GetBoundingBox(True)
    print(f"  Bounding Box:")
    print(f"    Min: ({bbox.Min.X:.3f}, {bbox.Min.Y:.3f}, {bbox.Min.Z:.3f})")
    print(f"    Max: ({bbox.Max.X:.3f}, {bbox.Max.Y:.3f}, {bbox.Max.Z:.3f})")
    
    # Print additional attributes if they exist
    print(f"\nADDITIONAL PROPERTIES:")
    if hasattr(obj_data, 'Url') and obj_data.Url:
        print(f"  URL: {obj_data.Url}")
    
    # Print render material if available
    if obj_data.MaterialIndex >= 0:
        material = sc.doc.Materials[obj_data.MaterialIndex]
        print(f"  Material Name: {material.Name}")
        print(f"  Material Color: {material.DiffuseColor}")
    
    # Print object type-specific properties
    if hasattr(geometry, 'Area'):
        print(f"  Area: {geometry.Area:.3f}")
    if hasattr(geometry, 'Volume'):
        print(f"  Volume: {geometry.Volume:.3f}")
    if hasattr(geometry, 'Length'):
        print(f"  Length: {geometry.Length:.3f}")
    
    print("=" * 50)

print("\nAttribute extraction complete!") 