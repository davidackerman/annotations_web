import copy
import struct
import numpy as np
import os
import re
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
    # Prefer the actual annotation entry's `type` field over the tool field —
    # the tool can disagree with the data (e.g. tool=annotateLine but entries
    # are type=point), and the tool has no entry for axis_aligned_bounding_box.
    for ann in layer.get("annotations") or []:
        if "type" in ann:
            return ann["type"]
    tool = layer.get("tool", "")
    tool_type = tool.split("annotate")[1].lower() if "annotate" in tool else ""
    if tool_type == "boundingbox":
        return "axis_aligned_bounding_box"
    return tool_type


def get_layer_source_url(layer):
    if "url" in layer["source"]:
        return layer["source"]["url"]
    else:
        return layer["source"]


def get_annotations(info_dict):
    precomputed_annotations = None
    local_annotations = None
    annotation_type = None
    print(info_dict["layers"])
    for layer in info_dict["layers"]:
        if layer["type"] == "annotation":
            print("found annotation layer", layer)
            if "precomputed" in get_layer_source_url(layer):
                (
                    annotation_type,
                    precomputed_annotations,
                ) = extract_precomputed_annotations(layer)
                # apply translation
                precomputed_annotations = apply_translation_to_annotations(
                    layer, precomputed_annotations
                )
            elif get_layer_source_url(layer) == "local://annotations":
                # then this is the local layer
                annotation_type, local_annotations = extract_local_annotations(layer)
    if precomputed_annotations is not None and local_annotations is not None:
        annotations = np.concatenate((precomputed_annotations, local_annotations))
    elif local_annotations is not None:
        annotations = local_annotations
    else:
        annotations = precomputed_annotations

    return annotation_type, annotations


def apply_translation_to_annotations(layer, annotations):
    if "transform" not in layer["source"]:
        input_dim_names = ["x", "y", "z"]
        dims_size = {"x": [1], "y": [1], "z": [1]}
    elif "inputDimensions" in layer["source"]["transform"]:
        input_dim_names = ["0", "1", "2"]
        dims_size = layer["source"]["transform"]["inputDimensions"]
    else:
        input_dim_names = ["x", "y", "z"]
        dims_size = layer["source"]["transform"]["outputDimensions"]

    output_dim_names = ["x", "y", "z"]
    dim_index_dict = {
        output_dim_name: list(dims_size.keys()).index(input_dim_name)
        for input_dim_name, output_dim_name in zip(input_dim_names, output_dim_names)
    }
    x_dims = dims_size[input_dim_names[0]]
    y_dims = dims_size[input_dim_names[1]]
    z_dims = dims_size[input_dim_names[2]]
    # apply scaling from the matrix
    if "transform" in layer["source"]:
        matrix = np.array(layer["source"]["transform"]["matrix"])
        scale_x = matrix[dim_index_dict["x"], dim_index_dict["x"]]
        scale_y = matrix[dim_index_dict["y"], dim_index_dict["y"]]
        scale_z = matrix[dim_index_dict["z"], dim_index_dict["z"]]

        annotations[:, dim_index_dict["x"]] *= scale_x
        annotations[:, dim_index_dict["y"]] *= scale_y
        annotations[:, dim_index_dict["z"]] *= scale_z

        if annotations.shape[1] == 6:
            annotations[:, dim_index_dict["x"] + 3] *= scale_x
            annotations[:, dim_index_dict["y"] + 3] *= scale_y
            annotations[:, dim_index_dict["z"] + 3] *= scale_z
    if "transform" not in layer["source"]:
        matrix = np.eye(4)
    else:
        matrix = np.array(layer["source"]["transform"]["matrix"])

    # do scaling first
    translation = np.array(matrix[0:3, 3])
    annotations[:, dim_index_dict["x"]] += (
        translation[dim_index_dict["x"]] * x_dims[0] / 1e-9
    )
    annotations[:, dim_index_dict["y"]] += (
        translation[dim_index_dict["y"]] * y_dims[0] / 1e-9
    )
    annotations[:, dim_index_dict["z"]] += (
        translation[dim_index_dict["z"]] * z_dims[0] / 1e-9
    )
    if annotations.shape[1] == 6:
        annotations[:, dim_index_dict["x"] + 3] += (
            translation[dim_index_dict["x"]] * x_dims[0] / 1e-9
        )
        annotations[:, dim_index_dict["y"] + 3] += (
            translation[dim_index_dict["y"]] * y_dims[0] / 1e-9
        )
        annotations[:, dim_index_dict["z"] + 3] += (
            translation[dim_index_dict["z"]] * z_dims[0] / 1e-9
        )

    return annotations


def extract_local_annotations(layer):
    # Handle source as plain string (no transform) vs dict with transform
    source = layer["source"]
    has_transform = isinstance(source, dict) and "transform" in source

    if has_transform:
        if "inputDimensions" in source["transform"]:
            input_dim_names = ["0", "1", "2"]
            dims_size = source["transform"]["inputDimensions"]
        else:
            input_dim_names = ["x", "y", "z"]
            dims_size = source["transform"]["outputDimensions"]

        output_dim_names = ["x", "y", "z"]
        dim_index_dict = {
            output_dim_name: list(dims_size.keys()).index(input_dim_name)
            for input_dim_name, output_dim_name in zip(
                input_dim_names, output_dim_names
            )
        }

        x_dims = dims_size[input_dim_names[0]]
        y_dims = dims_size[input_dim_names[1]]
        z_dims = dims_size[input_dim_names[2]]
    else:
        # no transform: assume x,y,z identity mapping, coordinates already in nm
        dim_index_dict = {"x": 0, "y": 1, "z": 2}
        x_dims = [1e-9]
        y_dims = [1e-9]
        z_dims = [1e-9]

    annotation_type = get_annotation_type(layer)
    if annotation_type in ("line", "axis_aligned_bounding_box"):
        rows = []
        for current_annotation in layer["annotations"]:
            # skip annotations with empty coordinates
            if not current_annotation.get("pointA") or not current_annotation.get(
                "pointB"
            ):
                continue
            rows.append(
                [
                    current_annotation["pointA"][dim_index_dict["x"]]
                    * x_dims[0]
                    * 1e9,
                    current_annotation["pointA"][dim_index_dict["y"]]
                    * y_dims[0]
                    * 1e9,
                    current_annotation["pointA"][dim_index_dict["z"]]
                    * z_dims[0]
                    * 1e9,
                    current_annotation["pointB"][dim_index_dict["x"]]
                    * x_dims[0]
                    * 1e9,
                    current_annotation["pointB"][dim_index_dict["y"]]
                    * y_dims[0]
                    * 1e9,
                    current_annotation["pointB"][dim_index_dict["z"]]
                    * z_dims[0]
                    * 1e9,
                ]
            )
        annotation_data = np.array(rows) if rows else np.zeros((0, 6))
    elif annotation_type == "point":
        rows = []
        for current_annotation in layer["annotations"]:
            # skip annotations with empty coordinates
            if not current_annotation.get("point"):
                continue
            rows.append(
                [
                    current_annotation["point"][dim_index_dict["x"]]
                    * x_dims[0]
                    * 1e9,
                    current_annotation["point"][dim_index_dict["y"]]
                    * y_dims[0]
                    * 1e9,
                    current_annotation["point"][dim_index_dict["z"]]
                    * z_dims[0]
                    * 1e9,
                ]
            )
        annotation_data = np.array(rows) if rows else np.zeros((0, 3))
    else:
        return None, None

    return annotation_type, annotation_data


def extract_precomputed_annotations(layer):
    base_directory = "/groups/cellmap/cellmap/"
    # Find the precomputed source URL (handles string, dict, or list sources)
    source_urls = _get_source_urls(layer)
    source_url = next(u for u in source_urls if "precomputed" in u)
    # Strip protocol prefix and any trailing "|neuroglancer-precomputed:" suffix
    path_part = source_url.split("dm11/")[1]
    path_part = path_part.split("|")[0].rstrip("/")
    annotation_index = base_directory + path_part + "/spatial0/0_0_0"
    with open(annotation_index, mode="rb") as file:
        annotation_index_content = file.read()

    # need to specify which bytes to read
    num_annotations = struct.unpack("<Q", annotation_index_content[:8])[0]
    if (len(annotation_index_content) - 8) % (
        ((6 + 2) * num_annotations * 4)
    ) == 0:  # if it is for a line, there are 6 coordinates to write (4 bytes each), +2 other info stuff?
        annotation_type = "line"
        coords_to_write = 6
    else:
        annotation_type = "point"
        coords_to_write = 3
    annotation_data = struct.unpack(
        f"<Q{coords_to_write*num_annotations}f",
        annotation_index_content[: 8 + coords_to_write * num_annotations * 4],
    )
    annotation_data = np.reshape(
        np.array(annotation_data[1:]), (num_annotations, coords_to_write)
    )

    return annotation_type, annotation_data


def _write_single_precomputed(output_directory, annotation_type, annotations):
    """Write a single set of annotations to precomputed format on disk."""
    os.makedirs(f"{output_directory}/spatial0", exist_ok=True)

    if annotation_type in ("line", "axis_aligned_bounding_box"):
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
                "chunk_size": [
                    int(max_extent - min_extent)
                    for max_extent, min_extent in zip(max_extents, min_extents)
                ],
                "grid_shape": [1, 1, 1],
                "key": "spatial0",
                "limit": 1,
            }
        ],
    }

    with open(f"{output_directory}/info", "w") as info_file:
        json.dump(info, info_file)

    return output_directory.replace(
        "/groups/cellmap/cellmap/ackermand/",
        "precomputed://https://cellmap-vm1.int.janelia.org/dm11/ackermand/",
    )


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

    precomputed_source = _write_single_precomputed(
        output_directory, annotation_type, annotations
    )
    return write_time, precomputed_source


def generate_new_url(info_dict, precomputed_source):
    precomputed_layer = None
    local_layer = None
    saved_annotations_layer = None
    for layer in info_dict["layers"]:
        if layer["type"] == "annotation":
            if "precomputed" in layer["source"]:
                precomputed_layer = layer
                precomputed_layer["source"] = precomputed_source
            elif get_layer_source_url(layer) == "local://annotations" and (
                get_annotation_type(layer)
                in [
                    "line",
                    "point",
                ]
            ):
                # remove local annotations
                local_layer = layer
                local_layer["annotations"] = []
            elif layer.get("name") == "saved_annotations":
                # Track existing saved_annotations layer for removal
                saved_annotations_layer = layer

    if precomputed_layer is None:
        # Remove old saved_annotations layer if it exists
        if saved_annotations_layer:
            info_dict["layers"].remove(saved_annotations_layer)

        precomputed_layer = {
            "type": "annotation",
            "source": precomputed_source,
            "tab": "source",
            "annotationColor": "#8b8b23",
            "name": "saved_annotations",
        }

        if local_layer and "shader" in local_layer:
            precomputed_layer["shader"] = local_layer["shader"]
            if "shaderControls" in local_layer:
                precomputed_layer["shaderControls"] = local_layer["shaderControls"]

        info_dict["layers"].append(precomputed_layer)

    new_url = "https://neuroglancer-demo.appspot.com/#!" + urllib.parse.quote(
        json.dumps(info_dict)
    )
    return new_url


def create_new_url_with_precomputed_annotations(neuroglancer_url):
    info_dict = json.loads(urllib.parse.unquote(neuroglancer_url.split("/#!")[1]))
    annotation_type, annotations = get_annotations(info_dict)
    write_time, precomputed_source = write_precomputed_annotations(
        annotation_type, annotations
    )
    return (
        annotation_type,
        annotations,
        write_time,
        generate_new_url(info_dict, precomputed_source),
    )


def _get_source_urls(layer):
    """Get all source URLs from a layer, handling string, dict, or list sources."""
    source = layer["source"]
    if isinstance(source, list):
        sources = source
    else:
        sources = [source]
    urls = []
    for s in sources:
        if isinstance(s, str):
            urls.append(s)
        elif isinstance(s, dict) and "url" in s:
            urls.append(s["url"])
    return urls


def get_all_annotation_layers(info_dict):
    """Extract each annotation layer separately.
    Returns list of (layer_name, annotation_type, annotations_array).
    Every annotation layer is included even if it has 0 annotations.
    """
    results = []
    for layer in info_dict["layers"]:
        if layer["type"] == "annotation":
            layer_name = layer.get("name", "annotations")
            source_urls = _get_source_urls(layer)
            has_precomputed = any("precomputed" in u for u in source_urls)
            has_local = any("local://" in u for u in source_urls)

            all_annotations = []
            annotation_type = None

            if has_precomputed:
                annotation_type, annotations = extract_precomputed_annotations(layer)
                annotations = apply_translation_to_annotations(layer, annotations)
                if annotations is not None and len(annotations) > 0:
                    all_annotations.append(annotations)

            if has_local:
                if layer.get("annotations"):
                    annotation_type_local, annotations = extract_local_annotations(
                        layer
                    )
                    if annotation_type is None:
                        annotation_type = annotation_type_local
                    if annotations is not None and len(annotations) > 0:
                        all_annotations.append(annotations)

            # Determine annotation type from tool if we still don't know
            if annotation_type is None:
                detected = get_annotation_type(layer)
                annotation_type = detected if detected else "point"

            if all_annotations:
                combined = (
                    np.concatenate(all_annotations)
                    if len(all_annotations) > 1
                    else all_annotations[0]
                )
            else:
                # Empty array with correct shape
                cols = 6 if annotation_type in ("line", "axis_aligned_bounding_box") else 3
                combined = np.zeros((0, cols))

            results.append((layer_name, annotation_type, combined))
    return results


def write_multiple_precomputed_annotations(annotation_layers):
    """Write multiple annotation layers to disk under a single timestamp.
    Args: annotation_layers - list of (layer_name, annotation_type, annotations_array)
    Returns: (write_time, list of (layer_name, precomputed_source_url))
    """
    write_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = "/groups/cellmap/cellmap/ackermand/neuroglancer_annotations/" + write_time
    while os.path.exists(base_dir):
        sleep(1)
        write_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = (
            "/groups/cellmap/cellmap/ackermand/neuroglancer_annotations/" + write_time
        )

    os.makedirs(base_dir)

    precomputed_sources = []
    seen_names = {}
    for layer_name, annotation_type, annotations in annotation_layers:
        # Skip empty layers — can't write empty precomputed files
        if len(annotations) == 0:
            continue

        # sanitize layer name for directory
        safe_name = re.sub(r"[^\w\-]", "_", layer_name)
        # handle duplicate names
        if safe_name in seen_names:
            seen_names[safe_name] += 1
            safe_name = f"{safe_name}_{seen_names[safe_name]}"
        else:
            seen_names[safe_name] = 0

        output_directory = os.path.join(base_dir, safe_name)
        precomputed_source = _write_single_precomputed(
            output_directory, annotation_type, annotations
        )
        precomputed_sources.append((layer_name, precomputed_source))

    return write_time, precomputed_sources


def generate_new_url_multiple(info_dict, precomputed_sources):
    """Generate a new neuroglancer URL adding precomputed sources into existing annotation layers.

    Instead of creating new layers, each precomputed source is added as an
    additional source within the matching annotation layer panel.

    Args: info_dict - parsed neuroglancer state (will be deep-copied)
          precomputed_sources - list of (layer_name, precomputed_source_url)
    Returns: new neuroglancer URL string
    """
    info_dict = copy.deepcopy(info_dict)

    # build lookup: layer_name -> precomputed_source_url
    source_by_name = {name: src for name, src in precomputed_sources}

    for layer in info_dict["layers"]:
        if layer["type"] != "annotation":
            continue

        layer_name = layer.get("name", "annotations")
        if layer_name not in source_by_name:
            continue

        precomputed_source = source_by_name[layer_name]

        # Clear inline annotations to save URL space — they're now precomputed
        layer["annotations"] = []

        # Build source list: keep the local source for adding new annotations,
        # drop any old precomputed sources, add the new precomputed one
        existing_source = layer["source"]
        if isinstance(existing_source, list):
            source_list = existing_source
        else:
            source_list = [existing_source]

        # Remove old precomputed sources
        source_list = [
            s
            for s in source_list
            if not (isinstance(s, str) and "precomputed" in s)
            and not (isinstance(s, dict) and "precomputed" in s.get("url", ""))
        ]

        # Add the new precomputed source alongside the local one
        source_list.append(precomputed_source)
        layer["source"] = source_list

    new_url = "https://neuroglancer-demo.appspot.com/#!" + urllib.parse.quote(
        json.dumps(info_dict)
    )
    return new_url


def create_new_url_with_multiple_precomputed_annotations(neuroglancer_url):
    """Orchestrator for multi-layer annotation extraction.
    Returns: (annotation_layers, write_time, new_url)
        annotation_layers: list of (layer_name, annotation_type, annotations_array)
    """
    info_dict = json.loads(urllib.parse.unquote(neuroglancer_url.split("/#!")[1]))
    annotation_layers = get_all_annotation_layers(info_dict)
    # Only write to disk and generate new URL if there are actual annotations
    has_data = any(len(a) > 0 for _, _, a in annotation_layers)
    if has_data:
        write_time, precomputed_sources = write_multiple_precomputed_annotations(
            annotation_layers
        )
        new_url = generate_new_url_multiple(info_dict, precomputed_sources)
    else:
        write_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_url = None
    return annotation_layers, write_time, new_url


def set_local_annotations(neuroglancer_url):
    info_dict = json.loads(urllib.parse.unquote(neuroglancer_url.split("/#!")[1]))

    _, annotations = get_annotations(info_dict)

    precomputed_layer = None
    for layer in info_dict["layers"]:
        if layer["type"] == "annotation":
            if "precomputed" in layer["source"]:
                precomputed_layer = layer
            elif get_layer_source_url(layer) == "local://annotations":
                voxel_dim = [
                    layer["source"]["transform"]["outputDimensions"]["x"][0] * 1e9,
                    layer["source"]["transform"]["outputDimensions"]["y"][0] * 1e9,
                    layer["source"]["transform"]["outputDimensions"]["z"][0] * 1e9,
                ]
                # remove local annotations
                local_layer = layer
                local_layer["annotations"] = []

    for id, annotation in enumerate(annotations):
        local_layer["annotations"].append(
            {
                "pointA": [annotation[i] / voxel_dim[i] for i in range(3)],
                "pointB": [annotation[i + 3] / voxel_dim[i] for i in range(3)],
                "type": "line",
                "id": f"{id}+1",
            }
        )
    if precomputed_layer:
        info_dict["layers"].remove(precomputed_layer)
    new_url = "https://neuroglancer-demo.appspot.com/#!" + urllib.parse.quote(
        json.dumps(info_dict)
    )
    return new_url
