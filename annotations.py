import os
import struct
import csv
#https://github.com/google/neuroglancer/issues/227
os.system("rm -rf jrc_hela-2/annotations")
#os.system("mkdir -p jrc_hela-2/annotations/spatial0")
os.system("mkdir jrc_hela-2/annotations/relationships")


file_path = f"/groups/cosem/cosem/ackermand/paperResultsWithFullPaths/analysisResults/HeLa2/generalObjectInformation/ribosomes_{classification}.csv"
coordinates = [] 
#center_path = "/groups/cosem/cosem/ackermand/paperResultsWithFullPaths/analysisResults/HeLa2/ribosomes_centers.csv")
count=0
with open(file_path, newline='') as data_file:
	reader = csv.DictReader(data_file)
	for row in reader:
		object_id = row['Object ID']
		x = float(row["COM X (nm)"])
		y = y_dimension - float(row["COM Y (nm)"])
		z = float(row["COM Z (nm)"])*z_scale
		coordinates.append(tuple((x,y,z)))
		count=count+1
		if count % 100000 == 0:
			print(count)

count = 0;
with open(f"jrc_hela-2/annotations/relationships/{relationship_id}",'wb') as outfile:
	total_count=len(coordinates) # coordinates is a list of tuples (x,y,z) 
	buf = struct.pack('<Q',total_count)
	for (x,y,z) in coordinates:
		pt_buf = struct.pack('<6f',x,y,z,10,10,10)
		buf+=pt_buf
		count=count+1
		if count % 100000 == 0:
			print(count)
	# write the ids at the end of the buffer as increasing integers 
	id_buf = struct.pack('<%sQ' % len(coordinates),*range(len(coordinates)))
	#id_buf = struct.pack('<%sQ' % len(coordinates), 3,1 )#s*range(len(coordinates)))
	buf+=id_buf
	outfile.write(buf)

relationship_id = relationship_id-1



# {"@type": "neuroglancer_annotations_v1",
# "dimensions": {
# 	"x" : [1, "nm"],
# 	"y" : [1, "nm"],
# 	"z" : [1, "nm"]
# 	},
# 	  "by_id" : {
#       "key" : "by_id"
#    },
# "lower_bound": [0,0,0],
# "upper_bound": [48000,6400,33368],
# "annotation_type": "ELLIPSOID",
# "properties": [],
# "relationships" : [
#  {"id" : "cytosolic",
#  "key" : "../annotations/relationships"
#  },
#  {"id" : "nuclear",
#  "key" : "../annotations/relationships"
#  },
#  {"id" : "planar",
#  "key" : "../annotations/relationships"
#  },
#  {"id" : "tubular",
#  "key" : "../annotations/relationships"
#  }
#  ],
#  "spatial" : []
      
# }