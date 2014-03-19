import os
import ogr
import json
import HILDEBRAND

BASED = r'C:\Users\data\\'
FILE_MASTER = dict()

def mk_json_feature(north, south, east, west, file, exts, misc):
    north = float(north)
    south = float(south)
    east = float(east)
    west = float(west)

    properties = dict()
    properties['PATH'] = './' + file.split('.')[0]
    properties['EXTS'] = exts
    properties['LAYERS'] = '0'
    properties['WEO_TYPE'] = 'WEO_FEATURE'
    properties['WEO_MISCELLANEOUS_FILE'] = misc

    geometry = {'type': 'Polygon', 'coordinates': [((west,north), (east,north), (east,south), (west,south), (west,north))]}

    feature = {'geometry': geometry, 'type': 'Feature', 'properties': properties}

    return feature

def mk_toc(features):
    lut_properties = {'0': 'WEOALL=WEOALL', 'WEO_TYPE': 'LOOK_UP_TABLE'}
    lut = {'geometry': None, 'type': 'Feature', 'properties': lut_properties}
    features.append(lut)

    geojson = dict()
    geojson['type'] = 'Featurefeatures'
    geojson['name'] = 'NewFeatureType'
    geojson['features'] = features

    output = open(('_ToC.json'), 'w')
    output.write(json.dumps(geojson, sort_keys=True, indent=4, separators=(',', ': ')))
    output.close()
    return

def mk_file_dict(base, ext, type):
    try:
        if base in FILE_MASTER:
            FILE_MASTER[base][type].append(ext)
        else:
            FILE_MASTER[base] = {type: [ext]}
    except KeyError:
        FILE_MASTER[base].update({type: [ext]})
    return

for path, dir, files in os.walk(BASED):
    for file in files:
        base = '.'.join(file.split('.')[:1])
        ext = '.'.join(file.split('.')[1:])
        if ext not in ['shp', 'dbf', 'prj', 'shx', 'sbn', 'sbx']:
            mk_file_dict(base, ext, 'misc')
        else:
            mk_file_dict(base, ext, 'data')

features = []
for file in FILE_MASTER:
    driver = ogr.GetDriverByName('ESRI Shapefile')
    input_features_datasource = driver.Open(BASED + file + '.shp')
    if input_features_datasource is None:
        print 'Could not open ' + file
        exit
    input_layer = input_features_datasource.GetLayer()
    west, east, north, south = input_layer.GetExtent()
    feat = mk_json_feature(north, south, east, west, file, ';'.join(FILE_MASTER[file]['data']), 'No')
    features.append(feat)

    if FILE_MASTER[file]['misc'] != []:
        feat = mk_json_feature(north, south, east, west, file, ';'.join(FILE_MASTER[file]['misc']), 'Yes')
        features.append(feat)
    else:
        pass

mk_toc(features)