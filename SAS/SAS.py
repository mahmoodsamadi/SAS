import random
import sys,os

import arcpy
from arcpy import env  
from arcpy.sa import *
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("spatial")

def get_path(xx):
	mytemp = xx.replace("'", "")
	mytemp_= arcpy.Describe(mytemp)
	return mytemp_.catalogPath

def my_fields(table, wildcard=None, fieldtype=None):
    fields = arcpy.ListFields(table, wildcard, fieldtype)
    nameList = []
    for field in fields:
        nameList.append(field.name)
    return nameList

def my_addfield(inFeatures, fieldname, type="n"):
	types={"s":"TEXT","n":"DOUBLE"}
	if fieldname in my_fields(inFeatures):
		return False
	else:
		arcpy.AddField_management(inFeatures, fieldname, types[type])
		return True

point_layer = get_path(arcpy.GetParameterAsText(0))
weight_field = arcpy.GetParameterAsText(1)
buffer = float(arcpy.GetParameterAsText(2))
HotSpots_buffer = float(arcpy.GetParameterAsText(3))
point_count = int(arcpy.GetParameterAsText(4))
boundary = arcpy.GetParameterAsText(5)
workspace = arcpy.GetParameterAsText(6)

buffer_l = workspace + "\\buffered.shp"
buffer_erased = workspace + "\\buffer_erased.shp"
HotSpots_l = workspace + "\\HotSpots.shp"
HotSpots_signif = workspace + "\\HotSpots_sig.shp"
HotSpots_signif_buffer =  workspace + "\\HotSpots_sig_buff.shp"
buffer_erased_final = workspace + "\\buffer_erased_final.shp"
outFC = workspace + "\\absence_samples.shp"

arcpy.Buffer_analysis(point_layer,buffer_l, "%s Meters"%buffer, "FULL", "ROUND", "NONE", "")
arcpy.Erase_analysis(boundary, buffer_l, buffer_erased,'#')

arcpy.HotSpots_stats(point_layer, weight_field, HotSpots_l,"FIXED_DISTANCE_BAND", "EUCLIDEAN_DISTANCE", "NONE","#", "#", "#","NO_FDR")
my_addfield(HotSpots_l, "buff_dis", type="n")
with arcpy.da.UpdateCursor(HotSpots_l, ["GiPValue", "GiZScore","buff_dis"]) as cursor:
	for row in cursor:
		if row[1] > 1.96 and row[0] < 0.05:
			row[2] = float(1)
		cursor.updateRow(row)

try:
	arcpy.AddField_management(inFeatures, "temp7788", "DOUBLE",18 ,11)
	arcpy.DeleteField_management(inFeatures, "temp7788")
except:
	pass

arcpy.Select_analysis(HotSpots_l, HotSpots_signif, "\"buff_dis\" = 1")
arcpy.Buffer_analysis(HotSpots_signif,HotSpots_signif_buffer, "%s Meters"%HotSpots_buffer, "FULL", "ROUND", "NONE", "")
arcpy.Erase_analysis(buffer_erased, HotSpots_signif_buffer, buffer_erased_final,'#')

def make_p(buffer_erased_final,point_count,outFC,point_layer):
	#all_points = getlocations(buffer_erased_final,point_count = point_count)
	outPath, outName = os.path.split(outFC)

	#minDistance = "600 Meters"
	minDistance = ""
	arcpy.CreateRandomPoints_management(outPath, outName, buffer_erased_final, "", point_count, minDistance) 

ANN = 0
best_res = 0
howmany = 50
numrun = 0

while ANN < 1:
	if numrun < howmany:
		numrun +=1
		make_p(buffer_erased_final,point_count,outFC,point_layer)
		nn_output = arcpy.AverageNearestNeighbor_stats(outFC, "EUCLIDEAN_DISTANCE", "NO_REPORT", "#")
		ANN = float(nn_output.getOutput(0))

		arcpy.AddMessage("NO %s"%numrun)
		arcpy.AddMessage("#######################")
		arcpy.AddMessage("The nearest neighbor index is: " + str(float(nn_output.getOutput(0))))
		arcpy.AddMessage("The z-score of the nearest neighbor index is: " + str(float(nn_output.getOutput(1))))
		arcpy.AddMessage("The p-value of the nearest neighbor index is: " + str(float(nn_output.getOutput(2))))
		arcpy.AddMessage("#######################")
		if ANN > best_res:

			if arcpy.Exists(workspace + "\\absence_samples_%s.shp"%str("temp")):
				arcpy.Delete_management(workspace + "\\absence_samples_%s.shp"%str("temp"))
			arcpy.CopyFeatures_management(outFC, workspace + "\\absence_samples_%s.shp"%str("temp"))
			best_res = ANN

	else:
		arcpy.CopyFeatures_management(workspace + "\\absence_samples_%s.shp"%str("temp"), outFC)
		arcpy.AddMessage("After %s times running, the best result of NNratio was selected."%howmany)
		arcpy.AddMessage("#######################")
		arcpy.AddMessage("The nearest neighbor index is: " + str(best_res))
		arcpy.AddMessage("#######################")

		break

for x in [workspace + "\\absence_samples_temp.shp",buffer_l,buffer_erased,HotSpots_signif_buffer,buffer_erased_final]:
	if arcpy.Exists(x):
		arcpy.Delete_management(x)
