"""
For imports from other scripts. Everything is self-contained in the .ipynb elsewise.
"""
print("Importing libraries...")
import open3d as o3d
import numpy as np
from cloudvolume import CloudVolume
from meshparty import trimesh_io
from cloudvolume import Bbox
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os
print("All libraries have been imported")

def get_em_images(em_src, bbox, mip_resolution:np.array=[16,16,40], save_dir:str='./objects/default_save/em_images'):
    em_cv = CloudVolume(em_src, mip=mip_resolution, bounded=False, fill_missing=True, use_https=True, progress=True)
    em = em_cv[bbox]
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        em.save_images(save_dir,)
    return em

def get_segmentation_images(seg_src, bbox, mip_resolution:np.array=[16,16,40], save_dir:str='./objects/default_save/segmentation_images', seg_ids:np.array=None):
    seg_cv = CloudVolume(seg_src, mip=mip_resolution, bounded=False, fill_missing=True, use_https=True, progress=True)
    seg = seg_cv[bbox]
    if seg_ids is not None:
        # set to 0 all the values that are not in seg_ids
        seg[np.isin(seg, seg_ids, invert=True)] = 0
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        seg.save_images(save_dir)
    return seg

def acquire_neuron_meshes(
    seg_ids:np.array, 
    color_map:dict, 
    use_bounds:bool=False, 
    min_bounds:np.array=[0,0,0], 
    max_bounds:np.array=[0,0,0], 
    output_dir:str='./objects/default_save', 
    offset:np.array=[0,0,0], 
    trimesh_meta:trimesh_io.MeshMeta=None):
    """
    Acquires the neuron meshes from the segmentation images and saves them as obj files.
    """
    if trimesh_meta is None:
        raise ValueError("Trimesh_meta must be provided")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for seg_id in seg_ids:
        try:
            print(f"Processing segment ID: {seg_id}")
            mesh = trimesh_meta.mesh(seg_id=int(seg_id))
            
            # Convert trimesh to Open3D format
            vertices = np.array(mesh.vertices)

            faces = np.array(mesh.faces)
            # Downsample the mesh
            #original_num_triangles = len(open3d_mesh.triangles)
            #target_number_of_triangles = max(original_num_triangles // downsampling_factor, 1)
            #simplified_mesh = open3d_mesh.simplify_quadric_decimation(target_number_of_triangles)
            # Filter the vertices based on bounding box
            vertex_flags = []
            filtered_vertices = []
            current_true_idx = 0

            if use_bounds:
                for i, (x, y, z) in enumerate(vertices):
                    if (min_bounds[0] <= x <= max_bounds[0] and
                        min_bounds[1] <= y <= max_bounds[1] and
                        min_bounds[2] <= z <= max_bounds[2]):

                        x -= offset[0]
                        y -= offset[1]
                        z -= offset[2]

                        vertex_flags.append((True, current_true_idx))
                        filtered_vertices.append([x, y, z])
                        current_true_idx += 1
                    else:
                        vertex_flags.append((False, None))

                filtered_faces = []
                for face in faces:
                    remapped_face_indices = []
                    for idx in face:
                        flag, new_idx = vertex_flags[idx]
                        if flag:
                            remapped_face_indices.append(new_idx)
                    
                    if len(remapped_face_indices) == 3: 
                        filtered_faces.append(remapped_face_indices)
            else:
                for x, y, z in vertices:
                    x -= offset[0]
                    y -= offset[1]
                    z -= offset[2]
                    filtered_vertices.append([x, y, z])
                filtered_faces = faces

            open3d_mesh = o3d.geometry.TriangleMesh()
            open3d_mesh.vertices = o3d.utility.Vector3dVector(np.array(filtered_vertices))
            open3d_mesh.triangles = o3d.utility.Vector3iVector(np.array(filtered_faces))

            if seg_id in color_map:
                color = color_map[seg_id]
            else:
                color = [1, 1, 1]  
            colors = np.tile(color, (len(filtered_vertices), 1))

            open3d_mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
            o3d.io.write_triangle_mesh(f'{output_dir}/seg_{seg_id}.obj', open3d_mesh)

            mesh_filename = f'{output_dir}/seg_{seg_id}.obj'
            material_filename = f'{output_dir}/seg_{seg_id}.mtl'
            relative_material_filename = f'seg_{seg_id}.mtl'

            with open(material_filename, 'w') as mtl_file:
                mtl_file.write(f"newmtl SegmentMaterial_{seg_id}\n")
                mtl_file.write(f"Kd {color[0]} {color[1]} {color[2]}\n")  # Diffuse color
                mtl_file.write(f"Ka {color[0]} {color[1]} {color[2]}\n")  # Ambient color
                mtl_file.write(f"Ks 1.0 1.0 1.0\n")  # Specular color
                mtl_file.write("Ns 1000\n")  # Specular exponent
            with open(mesh_filename, 'r') as obj_file:
                obj_lines = obj_file.readlines()
            with open(mesh_filename, 'w') as obj_file:
                obj_file.write(f"mtllib {relative_material_filename}\n") 
                obj_file.write(f"usemtl SegmentMaterial_{seg_id}\n")  
                obj_file.writelines(obj_lines)
            print(f"Processed segment ID: {seg_id} and saved to {mesh_filename} with material {material_filename}")
        except Exception as e:
            print(f"Error processing segment {seg_id}: {e}")
    print("All meshes have been processed, filtered and saved.")

