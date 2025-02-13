var uploaded_annotations = []
function UploadUsingCSVData() {
    //uploaded_annotations = []
    console.log("uploaded annotations"+uploaded_annotations)
    var fileUpload = document.getElementById("fileUpload");
    if (typeof (FileReader) != "undefined") {
        var reader = new FileReader();
        reader.onload = function (e) {
            var table = document.createElement("table");
            var rows = e.target.result.split("\n");
            for (var i = 0; i < rows.length; i++) {
                var cells = rows[i].split(",");
                if (cells.length > 1) {
                    var row = table.insertRow(-1);
                    var coordinates = []
                    for (var j = 0; j < 7; j++) {
                        var cell = row.insertCell(-1);
                        cell.innerHTML = cells[j];
                        coordinates.push(cells[j]);
                    }
                    if (i > 0) { // then it is not the title
                        console.log(i)
                        var current_annotation = {
                            "id": coordinates[0],
                            "pointA": [parseFloat(coordinates[1]), parseFloat(coordinates[2]), parseFloat(coordinates[3])],
                            "pointB": [parseFloat(coordinates[4]), parseFloat(coordinates[5]), parseFloat(coordinates[6])],
                            "type": "line",
                        }
                        uploaded_annotations.push(current_annotation)
                    }
                }
            }
            var dvCSV = document.getElementById("dvCSV");
            dvCSV.innerHTML = "";
            dvCSV.appendChild(table);
        }
        reader.readAsText(fileUpload.files[0]);
        console.log("uploaded annotations"+uploaded_annotations)
    } else {
        alert("This browser does not support HTML5.");
    }
}
function Upload() {
    uploaded_annotations = []
    var fileUpload = document.getElementById("fileUpload");
    if (typeof (FileReader) != "undefined") {
        var reader = new FileReader();
        reader.onload = function (e) {
            var rows = e.target.result.split("\n");
            var cells = rows[1].split(",");
            url = cells[8];
            var neuroglancer_json = JSON.parse(decodeURIComponent(url.split("#!")[1]));
            console.log(neuroglancer_json)
            for (var layer_idx in neuroglancer_json['layers']) {
                let layer = neuroglancer_json['layers'][layer_idx]
                if (layer['type'] == "annotation") {
                    uploaded_annotation_layer = layer;
                    break;
                }
            }
            console.log(uploaded_annotation_layer)
            var x_dims = uploaded_annotation_layer['source']['transform']['outputDimensions']["x"]
            var y_dims = uploaded_annotation_layer['source']['transform']['outputDimensions']["y"]
            var z_dims = uploaded_annotation_layer['source']['transform']['outputDimensions']["z"]

            var table = document.createElement("table");
            var row = table.insertRow(-1);
            row.insertCell(-1).innerHTML = "id"
            row.insertCell(-1).innerHTML = "start x (nm)"
            row.insertCell(-1).innerHTML = "start y (nm)"
            row.insertCell(-1).innerHTML = "start z (nm)"
            row.insertCell(-1).innerHTML = "end x (nm)"
            row.insertCell(-1).innerHTML = "end y (nm)"
            row.insertCell(-1).innerHTML = "end z (nm)"
            for (var j = 0; j < uploaded_annotation_layer['annotations'].length; j++) {
                var row = table.insertRow(-1);
                row.insertCell(-1).innerHTML = uploaded_annotation_layer['annotations'][j]["id"];
                row.insertCell(-1).innerHTML = uploaded_annotation_layer['annotations'][j]["pointA"][0] * x_dims[0] / 1e-9;
                row.insertCell(-1).innerHTML = uploaded_annotation_layer['annotations'][j]["pointA"][1] * y_dims[0] / 1e-9;
                row.insertCell(-1).innerHTML = uploaded_annotation_layer['annotations'][j]["pointA"][2] * z_dims[0] / 1e-9;
                row.insertCell(-1).innerHTML = uploaded_annotation_layer['annotations'][j]["pointB"][0] * x_dims[0] / 1e-9;
                row.insertCell(-1).innerHTML = uploaded_annotation_layer['annotations'][j]["pointB"][1] * y_dims[0] / 1e-9;
                row.insertCell(-1).innerHTML = uploaded_annotation_layer['annotations'][j]["pointB"][2] * z_dims[0] / 1e-9;
            }

            var dvCSV = document.getElementById("dvCSV");
            dvCSV.innerHTML = "";
            dvCSV.appendChild(table);
        }
        reader.readAsText(fileUpload.files[0]);
    } else {
        alert("This browser does not support HTML5.");
    }
}

function readFile(file){
    return new Promise((resolve, reject) => {
        var reader = new FileReader();
            reader.onload = () => {
                resolve(reader.result)
                var rows = reader.result.split("\n");
                var cells = rows[1].split(",");
                url = cells[8];
                hiddenElement = document.createElement("input")
                hiddenElement.setAttribute("id","hidden_url")
                hiddenElement.setAttribute("value",url)
            }
            reader.onerror = reject
            reader.readAsText(file)  
    });
  }


  function extract()   
  {   //if url provided
     //if url provided and has annotations, then get from other thing and append then 
     var url = document.getElementById('neuroglancer_URL').value;
     var neuroglancer_json = JSON.parse(decodeURIComponent( url.split("#!")[1] ));
     console.log(neuroglancer_json)
 
     var current_annotation_layer = null;
     var annotation_layer_idx = null;
     for (var layer_idx in neuroglancer_json['layers']) {
         let layer = neuroglancer_json['layers'][layer_idx]
         if(layer['type'] == "annotation"){
             current_annotation_layer = layer;
             annotation_layer_idx = layer_idx
             break;
         }
     }
     if (uploaded_annotations.length == 0) {
         alert("No annotations uploaded.");
     }
     else {
         if (!current_annotation_layer) {
             neuroglancer_json["layers"].push(uploaded_annotation_layer);
         }
         else {
             uploaded_annotation_layer = []
             //var x_scale = uploaded_annotation_layer['source']['transform']['outputDimensions']["x"][0] / current_annotation_layer['source']['transform']['outputDimensions']["x"][0]
             //var y_scale = uploaded_annotation_layer['source']['transform']['outputDimensions']["y"][0] / current_annotation_layer['source']['transform']['outputDimensions']["y"][0]
             //var z_scale = uploaded_annotation_layer['source']['transform']['outputDimensions']["z"][0] / current_annotation_layer['source']['transform']['outputDimensions']["z"][0]
             for (var j = 0; j < uploaded_annotations.length; j++) {
                 uploaded_annotation_layer['annotations'][j]["pointA"][0] = uploaded_annotations[j]['pointA'][0]
                 uploaded_annotation_layer['annotations'][j]["pointA"][1] = uploaded_annotations[j]['pointA'][1]
                 uploaded_annotation_layer['annotations'][j]["pointA"][2] = uploaded_annotations[j]['pointA'][2]
                 uploaded_annotation_layer['annotations'][j]["pointB"][0] = uploaded_annotations[j]['pointA'][0]
                 uploaded_annotation_layer['annotations'][j]["pointB"][1] = uploaded_annotations[j]['pointA'][1]
                 uploaded_annotation_layer['annotations'][j]["pointB"][2] = uploaded_annotations[j]['pointA'][2]
             }
             current_annotation_layer["annotations"] = current_annotation_layer["annotations"].concat(uploaded_annotation_layer["annotations"])
             neuroglancer_json['layers'][annotation_layer_idx] = current_annotation_layer
         } 
     }
     //console.log(uploaded_annotation_layer)
     //console.log(neuroglancer_json)
     //console.log("http://renderer.int.janelia.org:8080/ng/#!" + encodeURIComponent( JSON.stringify(neuroglancer_json) ));
     window.open("http://renderer.int.janelia.org:8080/ng/#!" + encodeURIComponent(JSON.stringify(neuroglancer_json)), '_blank');
 
 }
//             x_dims = layer['source']['transform']['outputDimensions']["x"]
//             y_dims = layer['source']['transform']['outputDimensions']["y"]
//             z_dims = layer['source']['transform']['outputDimensions']["z"]

//             for( var annotation_idx in layer['annotations']){
//                 current_annotation = layer['annotations'][annotation_idx];
//                 annotation_data.push(
//                     [current_annotation["id"],
//                     current_annotation["pointA"][0]*x_dims[0],
//                     current_annotation["pointA"][1]*y_dims[0],
//                     current_annotation["pointA"][2]*z_dims[0],
//                     current_annotation["pointB"][0]*x_dims[0],
//                     current_annotation["pointB"][1]*y_dims[0],
//                     current_annotation["pointB"][2]*z_dims[0],
//                 ]
//                 );
//             }
//         }
    
    
//     var csv_content = `id,start x (${x_dims[1]}),start y (${y_dims[1]}),start z (${z_dims[1]}),end x (${x_dims[1]}),end y (${y_dims[1]}),end z (${z_dims[1]})\n`;  
       
//      //merge the data with CSV  
//      annotation_data.forEach(function(row) {  
//         csv_content += row.join(',');  
//         csv_content += "\n";  
//      }); 

//      var hiddenElement = document.createElement('a');  
//      hiddenElement.href = 'data:text/csv;charset=utf-8,' + encodeURI(csv_content);  
//      hiddenElement.target = '_blank';  
       
//      //provide the name for the CSV file to be downloaded  
//      hiddenElement.download = 'annotations.csv';  
//      hiddenElement.click();  
// }  
