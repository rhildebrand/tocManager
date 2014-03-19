import os
import ogr
import json

BASED = r'C:\Users\data\\'
FILE_MASTER = dict()

def mk_json_feature(north, south, east, west, file, exts, misc):
    '''Make a polygonal JSON feature comprised of a Shapefile's bounding box
    plus additional infromation such as the base file name, all associated 
    extensions, and the type of WeoGeo feature it is.'''
    properties = dict()
    properties['PATH'] = './' + file.split('.')[0]
    properties['EXTS'] = exts
    properties['LAYERS'] = '0'
    properties['WEO_TYPE'] = 'WEO_FEATURE'
    properties['WEO_MISCELLANEOUS_FILE'] = misc

    geometry = {'type': 'Polygon', 'coordinates': [((west,north), (east,north),
                                                    (east,south), (west,south), 
                                                    (west,north))]}

    feature = {'geometry': geometry, 'type': 'Feature', 'properties': properties}

    return feature

def mk_toc(features):
    '''The last step in the process and handles the creation of the Look Up 
    Table and wraps all of the Table of Contents features in the necessary 
    JSON syntax. The file is then written out to the base directory'''
    lut_properties = {'0': 'WEOALL=WEOALL', 'WEO_TYPE': 'LOOK_UP_TABLE'}
    lut = {'geometry': None, 'type': 'Feature', 'properties': lut_properties}
    features.append(lut)

    geojson = dict()
    geojson['type'] = 'Featurefeatures'
    geojson['name'] = 'NewFeatureType'
    geojson['features'] = features

    output = open((BASED + 'WeoGeoTableOfContents.json'), 'w')
    output.write(json.dumps(geojson, sort_keys=True, 
                            indent=4, separators=(',', ': ')))
    output.close()
    return

def mk_file_dict(base, ext, type):
    '''Checks to see if a base file name already exists in the master 
    dictionary and if it does, then append its extension to the list 
    for which it is flagged.'''
    try:
        if base in FILE_MASTER:
            FILE_MASTER[base][type].append(ext)
        else:
            FILE_MASTER[base] = {type: [ext]}
    except KeyError:
        FILE_MASTER[base].update({type: [ext]})
    return

# Walk through the base directory and separate data files from miscellaneous
# files. The purpose is to have a dictionary with each key being a file name
# and the associated values being "data" + extensions and "misc" + extensions. 
for path, dir, files in os.walk(BASED):
    for file in files:
        base = '.'.join(file.split('.')[:1])
        ext = '.'.join(file.split('.')[1:])
        if ext not in ['shp', 'dbf', 'prj', 'shx', 'sbn', 'sbx']:
            mk_file_dict(base, ext, 'misc')
        else:
            mk_file_dict(base, ext, 'data')

# After the File Dictionary is made, iterate over it and extract the MBR from 
# each Shapefile and check to see if there are any miscellaneous files related 
# to that Shape. If there are, then make a JSON feature for that file using
# the MBR from its associated Shapefile. Then store all of these JSON features
# in a list to be used later. 
features = []
for file in FILE_MASTER:
    driver = ogr.GetDriverByName('ESRI Shapefile')
    input_features_datasource = driver.Open(BASED + file + '.shp')
    if input_features_datasource is None:
        print 'Could not open ' + file
        exit(0)
    input_layer = input_features_datasource.GetLayer()
    west, east, north, south = input_layer.GetExtent()
    feat = mk_json_feature(north, south, east, west, file, 
                           ';'.join(FILE_MASTER[file]['data']), 'No')
    features.append(feat)

    try:
        if FILE_MASTER[file]['misc'] != []:
            feat = mk_json_feature(north, south, east, west, file, 
                                ';'.join(FILE_MASTER[file]['misc']), 'Yes')
            features.append(feat)
    except KeyError:
        pass

mk_toc(features)