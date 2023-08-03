import struct
import numpy as np
import os
import struct
import numpy as np
import json
from time import sleep
from datetime import datetime
import urllib


def get_annotations_from_url(neuroglancer_url):
    info_dict = json.loads(urllib.parse.unquote(neuroglancer_url.split("/#!")[1]))
    annotations = get_annotations(info_dict)
    return annotations


def get_annotation_type(layer):
    # hacky way to get annotation type, we are currently assuming only one type of annotation is present for each layer
    # and that it is the currently selected annotation type
    return ["line" if layer["tool"] == "annotateLine" else "point"][0]


def get_annotations(info_dict):
    precomputed_annotations = None
    local_annotations = None
    annotation_type = None
    for layer in info_dict["layers"]:
        if layer["type"] == "annotation":
            if "precomputed" in layer["source"]:
                annotation_type, precomputed_annotations = extract_precomputed_annotations(layer)
            elif layer["source"]["url"] == "local://annotations":
                # then this is the local layer
                annotation_type, local_annotations = extract_local_annotations(layer)
 
    if precomputed_annotations is not None and local_annotations is not None:
        annotations = np.concatenate((precomputed_annotations, local_annotations))
    elif local_annotations is not None:
        annotations = local_annotations
    else:
        annotations = precomputed_annotations

    return annotation_type, annotations


def extract_local_annotations(layer):
    x_dims = layer["source"]["transform"]["outputDimensions"]["x"]
    y_dims = layer["source"]["transform"]["outputDimensions"]["y"]
    z_dims = layer["source"]["transform"]["outputDimensions"]["z"]
    annotation_type = get_annotation_type(layer)
    if annotation_type == "line":
        annotation_data = np.zeros((len(layer["annotations"]), 6))
        for idx, current_annotation in enumerate(layer["annotations"]):
            # assume that it is in url as m, so divide by 1e-9 to get it in nm
            annotation_data[idx, :] = [
                current_annotation["pointA"][0] * x_dims[0] * 1e9,
                current_annotation["pointA"][1] * y_dims[0] * 1e9,
                current_annotation["pointA"][2] * z_dims[0] * 1e9,
                current_annotation["pointB"][0] * x_dims[0] * 1e9,
                current_annotation["pointB"][1] * y_dims[0] * 1e9,
                current_annotation["pointB"][2] * z_dims[0] * 1e9,
            ]
    else:
        annotation_data = np.zeros((len(layer["annotations"]), 3))
        for idx, current_annotation in enumerate(layer["annotations"]):
            # assume that it is in url as m, so divide by 1e-9 to get it in nm
            annotation_data[idx, :] = [
                current_annotation["point"][0] * x_dims[0] * 1e9,
                current_annotation["point"][1] * y_dims[0] * 1e9,
                current_annotation["point"][2] * z_dims[0] * 1e9,
            ]
    return annotation_type, annotation_data


def extract_precomputed_annotations(layer):
    base_directory = "/groups/cellmap/cellmap/"
    annotation_index = (
        base_directory + layer["source"].split("dm11/")[1] + "/spatial0/0_0_0"
    )
    with open(annotation_index, mode="rb") as file:
        annotation_index_content = file.read()

    # need to specify which bytes to read
    num_annotations = struct.unpack("<Q", annotation_index_content[:8])[0]
    if (len(annotation_index_content)-8) % (((6+2)*num_annotations*4)) == 0: # if it is for a line, there are 6 coordinates to write (4 bytes each), +2 other info stuff?
        annotation_type = "line"
        coords_to_write = 6
    else:
        annotation_type = "point"
        coords_to_write = 3
    annotation_data = struct.unpack(
        f"<Q{coords_to_write*num_annotations}f",
        annotation_index_content[: 8 + coords_to_write * num_annotations * 4],
    )
    annotation_data = np.reshape(np.array(annotation_data[1:]), (num_annotations, coords_to_write))
    return annotation_type, annotation_data


def write_precomputed_annotations(annotation_type, annotations):
    write_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_directory = (
        "/groups/cellmap/cellmap/ackermand/neuroglancer_annotations/" + write_time
    )
    while os.path.exists(output_directory):
        sleep(1)
        write_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_directory = (
            "/groups/cellmap/cellmap/ackermand/neuroglancer_annotations/" + write_time
        )

    os.makedirs(f"{output_directory}/spatial0")

    if annotation_type == "line":
        coords_to_write = 6
    else:
        coords_to_write = 3

    with open(f"{output_directory}/spatial0/0_0_0", "wb") as outfile:
        total_count = len(annotations)
        buf = struct.pack("<Q", total_count)
        for annotation in annotations:
            annotation_buf = struct.pack(f"<{coords_to_write}f", *annotation)
            buf += annotation_buf
        # write the ids at the end of the buffer as increasing integers
        id_buf = struct.pack(
            f"<{total_count}Q", *range(1, len(annotations) + 1, 1)
        )  # so start at 1
        # id_buf = struct.pack('<%sQ' % len(coordinates), 3,1 )#s*range(len(coordinates)))
        buf += id_buf
        outfile.write(buf)
    
    min_extents = annotations.reshape((-1, 3)).min(axis=0) - 1
    max_extents = annotations.reshape((-1, 3)).max(axis=0) + 1
    min_extents = [int(min_extent) for min_extent in min_extents]
    max_extents = [int(max_extent) for max_extent in max_extents]
    info = {
        "@type": "neuroglancer_annotations_v1",
        "dimensions": {"x": [1, "nm"], "y": [1, "nm"], "z": [1, "nm"]},
        "by_id": {"key": "by_id"},
        "lower_bound": min_extents,
        "upper_bound": max_extents,
        "annotation_type": annotation_type,
        "properties": [],
        "relationships": [],
        "spatial": [
            {
                "chunk_size": [int(max_extent-min_extent) for max_extent,min_extent in zip(max_extents,min_extents)],
                "grid_shape": [1, 1, 1],
                "key": "spatial0",
                "limit": 1,
            }
        ],
    }

    with open(f"{output_directory}/info", "w") as info_file:
        json.dump(info, info_file)

    return write_time, output_directory.replace(
        "/groups/cellmap/cellmap/ackermand/",
        "precomputed://https://cellmap-vm1.int.janelia.org/dm11/ackermand/",
    )


def generate_new_url(info_dict, precomputed_source):
    precomputed_layer = None
    for layer in info_dict["layers"]:
        if layer["type"] == "annotation":
            if "precomputed" in layer["source"]:
                precomputed_layer = layer
                precomputed_layer["source"] = precomputed_source
            elif layer["source"]["url"] == "local://annotations":
                # remove local annotations
                local_layer = layer
                local_layer["annotations"] = []

    if precomputed_layer is None:
        precomputed_layer = {
            "type": "annotation",
            "source": precomputed_source,
            "tab": "source",
            "annotationColor": "#8b8b23",
            "name": "saved_annotations",
        }

        if "shader" in local_layer:
            precomputed_layer["shader"] = local_layer["shader"]
            precomputed_layer["shaderControls"] = local_layer["shaderControls"]
        
        info_dict["layers"].append(precomputed_layer)

    new_url = "http://renderer.int.janelia.org:8080/ng/#!" + urllib.parse.quote(
        json.dumps(info_dict)
    )
    return new_url


def create_new_url_with_precomputed_annotations(neuroglancer_url):
    info_dict = json.loads(urllib.parse.unquote(neuroglancer_url.split("/#!")[1]))
    annotation_type, annotations = get_annotations(info_dict)
    write_time, precomputed_source = write_precomputed_annotations(annotation_type, annotations)
    return annotation_type, annotations, write_time, generate_new_url(info_dict, precomputed_source)


def set_local_annotations(neuroglancer_url):
    info_dict = json.loads(urllib.parse.unquote(neuroglancer_url.split("/#!")[1]))

    _, annotations = get_annotations(info_dict)

    precomputed_layer = None
    for layer in info_dict["layers"]:
        if layer["type"] == "annotation":
            if "precomputed" in layer["source"]:
                precomputed_layer = layer
            elif layer["source"]["url"] == "local://annotations":
                voxel_dim = [
                    layer["source"]["transform"]["outputDimensions"]["x"][0] * 1e9,
                    layer["source"]["transform"]["outputDimensions"]["y"][0] * 1e9,
                    layer["source"]["transform"]["outputDimensions"]["z"][0] * 1e9
                    ]
                # remove local annotations
                local_layer = layer
                local_layer["annotations"] = []

    for id, annotation in enumerate(annotations):
        local_layer["annotations"].append(
            {
                "pointA": [annotation[i]/voxel_dim[i] for i in range(3)],
                "pointB":  [annotation[i+3]/voxel_dim[i] for i in range(3)],
                "type": "line",
                "id": f'{id}+1'
            }
        )
    if precomputed_layer:
        info_dict["layers"].remove(precomputed_layer)
    new_url = "http://renderer.int.janelia.org:8080/ng/#!" + urllib.parse.quote(
        json.dumps(info_dict)
    )
    return new_url
