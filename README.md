# annotations-web

A small Flask app for extracting, editing, and re-uploading [Neuroglancer](https://github.com/google/neuroglancer) point/line/bounding-box annotations, built for CellMap workflows.

Given a Neuroglancer state URL, the app reads the annotation layers, converts local annotations to precomputed annotations on disk, and returns a new Neuroglancer URL pointing at the precomputed data, along with the annotations exported as CSV/Excel.

## Structure

- `annotations_flask/` — the Flask application
  - `app.py` — routes/endpoints
  - `utils/neuroglancer.py` — core logic for parsing Neuroglancer state, extracting/writing precomputed annotations, and generating updated URLs
  - `templates/`, `static/` — page templates and JS for the web UI
- `annotations.py`, `annotations.ipynb` — standalone script/notebook versions of the annotation workflow
- `corrections_for_hannah.ipynb` — one-off notebook for manual annotation corrections
- `old_files/` — legacy HTML/JS, kept for reference
- `info` — example Neuroglancer precomputed annotations `info` file

## Routes

- `/get_annotations` — extract annotations from a single-layer Neuroglancer URL, write them as precomputed, and download as CSV
- `/get_multiple_annotations` — same, but across multiple annotation layers, exported as a multi-sheet Excel workbook
- `/download_excel/<filename>` — download a previously generated Excel export
- `/set_annotations` — upload/set annotations back onto a Neuroglancer state
- `/get_editable_annotations` — convert a Neuroglancer URL's annotations to a locally editable layer

## Running

```bash
cd annotations_flask
python app.py
```

The app runs on `0.0.0.0` with debug mode enabled, and redirects `/` to `/get_annotations`.
