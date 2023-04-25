import struct
import numpy as np
import os
import struct
import numpy as np
import json
from time import sleep
from datetime import datetime
import urllib


def get_annotations(info_dict):
    precomputed_annotations = None
    local_annotations = None
    for layer in info_dict["layers"]:
        if layer["type"] == "annotation":
            if "precomputed" in layer["source"]:
                precomputed_annotations = extract_precomputed_annotations(layer)
            elif layer["source"]["url"] == "local://annotations":
                # then this is the local layer
                local_annotations = extract_local_annotations(layer)

    if precomputed_annotations is not None:
        annotations = np.concatenate((precomputed_annotations, local_annotations))
    else:
        annotations = local_annotations
    return annotations


def extract_local_annotations(layer):
    x_dims = layer["source"]["transform"]["outputDimensions"]["x"]
    y_dims = layer["source"]["transform"]["outputDimensions"]["y"]
    z_dims = layer["source"]["transform"]["outputDimensions"]["z"]

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
    return annotation_data


def extract_precomputed_annotations(layer):
    base_directory = "/groups/cellmap/cellmap/"
    annotation_index = (
        base_directory + layer["source"].split("dm11/")[1] + "/spatial0/0_0_0"
    )
    with open(annotation_index, mode="rb") as file:
        annotation_index_content = file.read()

    # need to specify which bytes to read
    num_annotations = struct.unpack("<Q", annotation_index_content[:8])[0]
    annotation_data = struct.unpack(
        f"<Q{6*num_annotations}f",
        annotation_index_content[: 8 + 6 * num_annotations * 4],
    )
    annotation_data = np.reshape(np.array(annotation_data[1:]), (num_annotations, 6))
    return annotation_data


def write_precomputed_annotations(annotations):
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
    with open(f"{output_directory}/spatial0/0_0_0", "wb") as outfile:
        total_count = len(annotations)  # coordinates is a list of tuples (x,y,z)
        buf = struct.pack("<Q", total_count)
        for annotation in annotations:
            line_buf = struct.pack("<6f", *annotation)  # x,y,z,10,10,10)
            buf += line_buf
        # write the ids at the end of the buffer as increasing integers
        id_buf = struct.pack(
            f"<{total_count}Q", *range(1, len(annotations) + 1, 1)
        )  # so start at 1
        # id_buf = struct.pack('<%sQ' % len(coordinates), 3,1 )#s*range(len(coordinates)))
        buf += id_buf
        outfile.write(buf)

    max_extents = annotations.reshape((-1, 3)).max(axis=0) + 1
    max_extents = [int(max_extent) for max_extent in max_extents]
    info = {
        "@type": "neuroglancer_annotations_v1",
        "dimensions": {"x": [1, "nm"], "y": [1, "nm"], "z": [1, "nm"]},
        "by_id": {"key": "by_id"},
        "lower_bound": [0, 0, 0],
        "upper_bound": max_extents,
        "annotation_type": "LINE",
        "properties": [],
        "relationships": [],
        "spatial": [
            {
                "chunk_size": max_extents,
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
            "shader": local_layer["shader"],
            "shaderControls": local_layer["shaderControls"],
            "name": "saved_annotations",
        }
        info_dict["layers"].append(precomputed_layer)

    new_url = "http://renderer.int.janelia.org:8080/ng/#!" + urllib.parse.quote(
        json.dumps(info_dict)
    )
    return new_url


def create_new_url_with_precomputed_annotations(neuroglancer_url):
    info_dict = json.loads(urllib.parse.unquote(neuroglancer_url.split("/#!")[1]))
    annotations = get_annotations(info_dict)
    write_time, precomputed_source = write_precomputed_annotations(annotations)
    return annotations, write_time, generate_new_url(info_dict, precomputed_source)
