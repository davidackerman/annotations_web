# app.py
import csv
from io import StringIO
import webbrowser
from flask import Flask, make_response, render_template, request, redirect
from flask import jsonify
from utils.neuroglancer import (
    create_new_url_with_precomputed_annotations,
    set_local_annotations,
)
import numpy as np

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return redirect("/get_annotations")


@app.route("/get_annotations", methods=["GET", "POST"])
def get_annotations():
    new_url = None
    write_time = None
    if request.method == "POST":
        neuroglancer_url = request.values.get("neuroglancer_url")
        (
            annotation_type,
            all_annotations,
            write_time,
            new_url,
        ) = create_new_url_with_precomputed_annotations(neuroglancer_url)
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        if annotation_type == "line":
            writer.writerow(
                [
                    "id",
                    "start x (nm)",
                    "start y (nm)",
                    "start z (nm)",
                    "end x (nm)",
                    "end y (nm)",
                    "end z (nm)",
                    "",
                    "neuroglancer url",
                ]
            )
        else:
            writer.writerow(
                [
                    "id",
                    "x (nm)",
                    "y (nm)",
                    "z (nm)",
                    "",
                    "neuroglancer url",
                ]
            )
        for idx in range(all_annotations.shape[0]):
            if idx == 0:
                writer.writerow([idx + 1, *all_annotations[idx, :], "", new_url])
            else:
                writer.writerow([idx + 1, *all_annotations[idx, :]])
        # return output
        return {
            "csv_data": csv_data.getvalue(),
            "new_url": new_url,
            "write_time": write_time,
        }
    return render_template("get_annotations.html")


@app.route("/set_annotations", methods=["GET", "POST"])
def set_annotations():
    return render_template("set_annotations.html")


@app.route("/get_editable_annotations", methods=["GET", "POST"])
def get_editable_annotations():
    new_url = None
    if request.method == "POST":
        neuroglancer_url = request.values.get("neuroglancer_url")
        new_url = set_local_annotations(neuroglancer_url)
        return {
            "new_url": new_url,
        }
    return render_template("get_editable_annotations.html")


# A function to add two numbers
@app.route("/add")
def add():
    a = request.args.get("a")
    b = request.args.get("b")
    return jsonify({"result": a + b})


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
