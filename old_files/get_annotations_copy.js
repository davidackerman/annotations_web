function extract()   
 {   
    let url = document.getElementById('neuroglancer_URL').value;
    let neuroglancer_json = JSON.parse(decodeURIComponent( url.split("#!")[1] ));
    var annotation_data = [];
    for (var layer_idx in neuroglancer_json['layers']) {
        let layer = neuroglancer_json['layers'][layer_idx]
        if(layer['type'] == "annotation"){
            x_dims = layer['source']['transform']['outputDimensions']["x"]
            y_dims = layer['source']['transform']['outputDimensions']["y"]
            z_dims = layer['source']['transform']['outputDimensions']["z"]

            for( var annotation_idx in layer['annotations']){
                current_annotation = layer['annotations'][annotation_idx];
                //assume that it is in url as m, so divide by 1e-9 to get it in nm
                console.log(current_annotation["pointA"][0])
                annotation_data.push(
                    [current_annotation["id"],
                        current_annotation["pointA"][0] * x_dims[0] * 1e9,
                        current_annotation["pointA"][1] * y_dims[0] * 1e9,
                        current_annotation["pointA"][2] * z_dims[0] * 1e9,
                        current_annotation["pointB"][0] * x_dims[0] * 1e9,
                        current_annotation["pointB"][1] * y_dims[0] * 1e9,
                        current_annotation["pointB"][2] * z_dims[0] * 1e9,
                ]
                );
            }
        }
    }
    
    //again assume nm, otherwise would use z (${z_dims[1]})
    var csv_content = `id,start x (nm),start y (nm),start z (nm),end x (nm),end y (nm),end z (nm),,neuroglancer url\n`;  
       
     //merge the data with CSV 
     var rowCount = 0;
     annotation_data.forEach(function(row) {  
        csv_content += row.join(',');  
        if (rowCount==0){ csv_content +=',,'+url;}// "http://renderer.int.janelia.org:8080/ng/#!"+decodeURIComponent(url.split("#!")[1]) ; }
        csv_content += "\n";  
        rowCount ++; 
     }); 
     //console.log(decodeURI(encodeURI( url)));
     var hiddenElement = document.createElement('a');  
     hiddenElement.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv_content);  
     //console.log( hiddenElement.href )
     hiddenElement.target = '_blank';  
       
     //provide the name for the CSV file to be downloaded  
     hiddenElement.download = 'annotations.csv';  
     hiddenElement.click();  
}  
