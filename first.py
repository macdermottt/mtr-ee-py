#!/Users/tobin/.pyenv/versions/2.7.8/bin/python

print "Content-type: application/json\n\n"
execfile('/Users/tobin/Sites/wp/earth/ee/bin/activate_this.py', dict(__file__='/Users/tobin/Sites/wp/earth/ee/bin/activate_this.py'))

import ee 
import cgi
import json


def getEEstuff( lat, lng ):

    point = [float(lng), float(lat) ]
    geom = {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [125.6, 10.1]
      },
      "properties": {
        "name": "Dinagat Islands"
      }
    }

    cover_names = ['Grass', 'Woods', 'Paved']

    ee.Initialize()

    collection = ee.ImageCollection('USDA/NAIP/DOQQ').filterDate('2010-04-01', '2014-07-01')
    median = collection.median()

    fc = ee.FeatureCollection('ft:1oWwsLFRfsKIO_Ya1QgxVFh-cQmYnok0FXIUVaxO0')

    cl = median.trainClassifier(['R','G','B','N'],None,None,None,fc,'class',"EPSG:4326",[0.00004491576420597607,0, -180,0,-0.00004491576420597607,90])

    new_img = median.classify( cl )

    def makeFeature( point ):
        geom['geometry']['coordinates'] = point
        return ee.Feature(geom)



    feat = makeFeature( point )
    clip = new_img.clip(feat.buffer(3218.688)) # that's 2 miles in meters
    data = clip.reduceRegion(ee.Reducer.histogram(),None, 5)
    try:
        hist = data.get('classification').getInfo()['histogram']
        named_hist = {}

        for i in range( 0, len( hist )) :
            named_hist[cover_names[i]] = hist[i]

        mapInfo = clip.getMapId({'min': 1, 'max': 3, 'palette': 'addd8e,31a354,f7fcb9'} )
    except TypeError:
        return {'status': "failure"}

    ret = {'status':'success', 'hist': named_hist, 'mapid' : mapInfo['mapid'], 'token': mapInfo['token'] }
    return ret 

form = cgi.FieldStorage()
lat = form.getfirst("lat", "")
lng = form.getfirst("lng", "")


print json.dumps( getEEstuff( lat, lng ) )
