import os
import json
import argparse
from osgeo import ogr
from osgeo import osr
from osgeo import gdal

FILE_MASTER = dict()

def mk_json_feature(north, south, east, west, file, exts, misc):
    '''Make a polygonal JSON feature comprised of a Shapefile's bounding box
    plus additional infromation such as the base file name, all associated 
    extensions, and the type of WeoGeo feature it is.'''
    properties = dict()
    properties['PATH'] = './' + file
    properties['EXTS'] = exts
    properties['LAYERS'] = '0'
    properties['WEO_TYPE'] = 'WEO_FEATURE'
    properties['WEO_MISCELLANEOUS_FILE'] = misc

    geometry = {'type': 'Polygon', 'coordinates': [((west,north), (east,north),
                                                    (east,south), (west,south), 
                                                    (west,north))]}

    feature = {'geometry': geometry, 'type': 'Feature', 'properties': properties}

    return feature

def mk_json_feature_point(lon, lat, file, exts, misc):
    '''Make a JSON point feature instead of a polygon.'''
    properties = dict()
    properties['PATH'] = './' + file
    properties['EXTS'] = exts
    properties['LAYERS'] = '0'
    properties['WEO_TYPE'] = 'WEO_FEATURE'
    properties['WEO_MISCELLANEOUS_FILE'] = misc

    geometry = {'type': 'Point', 'coordinates': [lon, lat]}

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
    geojson['type'] = 'FeatureCollection'
    geojson['name'] = 'NewFeatureType'
    geojson['features'] = features

    output = open((OPTIONS.BASEDIR + 'WeoGeoTableOfContents.json'), 'w')
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
def main():
    for path, dir, files in os.walk(OPTIONS.BASEDIR):
        for file in files:
            # FIX_ME: Need to account for multi-part extensions like shp.xml.
            base = '.'.join((os.path.join(path.replace(OPTIONS.BASEDIR, ''), file)).split('.')[:-1])
            ext = '.'.join(file.split('.')[-1:])

            if ext not in ['shp', 'dbf', 'prj', 'shx', 'sbn', 'sbx', 'tif']:
                mk_file_dict(base.replace('\\', '/'), ext, 'misc')
            else:
                mk_file_dict(base.replace('\\', '/'), ext, 'data')
    
    # After the File Dictionary is made, iterate over it and extract the MBR from 
    # each Shapefile and check to see if there are any miscellaneous files related 
    # to that Shape. If there are, then make a JSON feature for that file using
    # the MBR from its associated Shapefile. Then store all of these JSON features
    # in a list to be used later. 
    features = []
    for file in FILE_MASTER:
        if 'data' in FILE_MASTER[file]:
            if OPTIONS.DATA_TYPE == 'vector':
                d = ogr.GetDriverByName(OPTIONS.FILE_FORMAT)
                input_features_datasource = d.Open(OPTIONS.BASEDIR + file + '.' + FILE_MASTER[file]['data'][0])
                if input_features_datasource is None:
                    print 'Could not open ' + file
                    exit(0)
                input_layer = input_features_datasource.GetLayer()

                # This conditional handles POINT vectors instead of polygons.
                if input_layer.GetGeomType() == 1:
                    point = input_layer.GetNextFeature()
                    geom = point.GetGeometryRef()
                    longitude = geom.GetX()
                    latitude = geom.GetY()
                    feat = mk_json_feature_point(longitude, latitude, file, ';'.join(FILE_MASTER[file]['data']), 'No')
                    features.append(feat)
                    continue
                else:
                    west, east, north, south = input_layer.GetExtent()

            else:
                d = gdal.Open(OPTIONS.BASEDIR + file + '.' + FILE_MASTER[file]['data'][0])
                geo_info = d.GetGeoTransform()
                data_crs = osr.SpatialReference()
                data_crs.ImportFromWkt(d.GetProjectionRef())
                out_crs = osr.SpatialReference()
                out_crs.ImportFromEPSG(4326)
                transform = osr.CoordinateTransformation(data_crs, out_crs)
                
                west, south, z = transform.TransformPoint(geo_info[0], geo_info[3] + d.RasterXSize*geo_info[4] + d.RasterYSize*geo_info[5])
                east, north, z = transform.TransformPoint(geo_info[0] + d.RasterXSize*geo_info[1] + d.RasterYSize*geo_info[2], geo_info[3])

            feat = mk_json_feature(north, south, east, west, file, 
                                ';'.join(FILE_MASTER[file]['data']), 'No')
            features.append(feat)
        else:
            feat = mk_json_feature(90.0, -90.0, 180.0, -180.0, file, 
                                ';'.join(FILE_MASTER[file]['misc']), 'Yes')
            features.append(feat)
    
        try:
            if FILE_MASTER[file]['data'] != [] and FILE_MASTER[file]['misc'] != []:
                feat = mk_json_feature(north, south, east, west, file, 
                                    ';'.join(FILE_MASTER[file]['misc']), 'Yes')
                features.append(feat)
        except KeyError:
            pass

    mk_toc(features)

    return

if __name__ == '__main__':
    global OPTIONS
    parser = argparse.ArgumentParser(description='Table of Contents creator for WeoGeo Listings.')
    parser.add_argument('-B', '--BASEDIR', required=True,
                         help='Enter the absolute path to the base directory of the data files.')
    parser.add_argument('-F', '--FILE_FORMAT', required=False, default='ESRI Shapefile',
                         help='Enter the geospatial file format. (GDAL)')
    parser.add_argument('-D', '--DATA_TYPE', required=False, default='vector',
                         help='Enter raster or vector depending on the geospatial data.')
    OPTIONS = parser.parse_args()
    main()