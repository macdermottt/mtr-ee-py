execfile('/Users/tobin/Sites/wp/earth/ee/bin/activate_this.py', dict(__file__='/Users/tobin/Sites/wp/earth/ee/bin/activate_this.py'))

import ee 
import sys
ee.Initialize()
"""
00 ACAR - Landsat 5 Analysis by County

This Script generates a full analysis by county of mined areas
and distance to mining for communities in the "Appalachian 
Communities at Risk" application for iLoveMountains.org

"""
# Set up initial parameters for the analysis
NDVI_Year = sys.argv[2]
meterToMiles = 1609
NDVI_Threshold = 0.4
"""
Create a greenest pixel LANDSAT composite for the selected year, clip it
to a 1-mile buffer around the selected county and add layer to map
"""

def createMtrRaster( year ):

    composite = ee.Image(ee.ImageCollection('LANDSAT/LT5_L1T_ANNUAL_GREENEST_TOA')
          .filterDate( str(NDVI_Year) + '-01-01', str(NDVI_Year) + '-12-31')
          .first())

    """
    Calculate NDVI values from the greenest pixel composite and
    add this layer to the map
    """

    gp_ndvi = composite.expression(
      '(nir - red) / (nir + red)',
      {
        'red': composite.select('B3'),
        'nir': composite.select('B4')
      })

    """ 
    Construct a binary layer of NDVI values that are below the threshold 
    set previously and add it to map. This layer will include both active 
    mining and developed (i.e. urban) areas with low NDVI signatures.
    """

    blank = ee.Image(0) 
    NDVI_val = gp_ndvi.select('B4') 
    output = blank.where(NDVI_val.lte(NDVI_Threshold), 1) 
    LowNDVIresult = output.mask(output) 

    """ 
    Apply the mask created by Skytruth of roads, rivers and urban areas
    in order to segregate mined areas from developed areas in valleys that
    have similar NDVI signatures. To minimize the inadvertent masking out of
    legitimate mined areas next to roads and streams, eliminate areas 
    that have been permitted for mining from the mask by adding them to a
    reverse mask of the image generated by Skytruth
    """

    # Make feature collections of active and inactive surface mine permits

    ActivePermitsFC = ee.FeatureCollection("ft:1Fj2bNu-11Gr5eMsdkshtoLqg6P4u6XoJSEIzBrhG")
        

    InactivePermitsFC = ee.FeatureCollection( 'ft:1gd2y5e8D9jm0A8T75hwqnVFbheZdzReNIpysqQP6')
       

    # Add the Skytruth mask layer and create a reverse mask

    # masklayer_AV = ee.Image('GME/images/06136759344167181854-04511489441853393048').clip(CountyBuffer)
    # masklayer_30m = ee.Image('GME/images/06136759344167181854-02930370301135541999').clip(CountyBuffer)
    masklayer_60m = ee.Image('GME/images/06136759344167181854-16131000296591132522')#.clip(CountyBuffer)
    # masklayer_120m = ee.Image('GME/images/06136759344167181854-15792288749316527627').clip(CountyBuffer)
        
    blankMask = ee.Image(0) 
    MaskVal = masklayer_60m.select('b1') 
    MaskOutput = blankMask.where(MaskVal.gt(0), 1) 
    MaskResult = MaskOutput.mask(MaskOutput) 

    masklayer_reverse = MaskOutput.mask( MaskOutput.Not() )

    # Paint mine permit feature collections onto the reverse mask

    masklayer = masklayer_reverse.paint(ActivePermitsFC).paint(InactivePermitsFC) 

    # Select low-NDVI value areas that are within the reverse mask

    MTRresult = LowNDVIresult.And(masklayer)
    
    return MTRresult


"""
Select a county and create a 1-mile buffer around it to use
to clip all layers and analyze one county at a time. Then zoom
map to the center of the county
"""

CountyFC = ee.FeatureCollection( 'ft:1v5OEHqR7rg425zEMjCYiCZLnWkZEP4clwZG2btvZ')

"""
Get the layer of populated places and filter it to the actual 
boundaries of the county. Then create a function to calculate 1-mile 
buffers around each community.
"""

PopPlaces = ee.FeatureCollection( 'ft:19h17oltHKf-X4OfU7jN1EPHsG1pF-yFfP06gt236') 

def calcStats( countyName, mtrArea ):

    County = CountyFC.filterMetadata('State-County', 'equals', countyName) 

    FilteredPopPlaces = PopPlaces.filterBounds(County) 

    def buffer_er(feature) :
      buffered = feature.buffer(meterToMiles)
      return buffered

    bufferedPlaces = FilteredPopPlaces.map(buffer_er) 

    """
    Create a feature class from the raster image of active mining. 
    This operation is restricted to a 1-mile radius around communities
    in order to cut down on the processing time. Then subtract the
    active mining layer from the buffered communities in order to calculate 
    the unmined area within a 1-mile radius of each community.
    """

    MTRnearCommunities = mtrArea.reduceToVectors(None , bufferedPlaces, 25) 
    
    flatMTR = ee.Feature(MTRnearCommunities.geometry(25)) 

    def differ( feature ):
      return feature.difference(flatMTR, 25)

    NoMTRwithinMile = bufferedPlaces.map( differ )

    """
    Create and run defs to calculate the nearest distance 
    to active mining and area within a 1-mile radius that is NOT 
    classified as active mining for each community in the county
    """

    def area_er(  feat ):
      area = feat.area(25)
      return feat.set({'area':area})

    def dist_er( feat ):
      dist = feat.distance(flatMTR, 25)
      return feat.set('dist', dist)

    areas = NoMTRwithinMile.map( area_er )
    dists = FilteredPopPlaces.map(dist_er)


    def addDist(area_feat):
      dist_feat = dists.filterMetadata("FEATURE_ID", "equals", area_feat.get("FEATURE_ID")).first()
      return area_feat.set("dist", dist_feat.get('dist'))

    areasWithDist = areas.map(addDist)
    
    return areasWithDist

def csvWrite(csv, id_num, dist, area ):
    csv.write("{yr},{id},{d},{a}\n".format( yr = NDVI_Year, id=int(id_num), d = dist, a = area ))



year = sys.argv[2]
mtrArea = createMtrRaster( year )


county = sys.argv[1]

print("now working on " +  county + " for " + year )
a_with_d = calcStats( county, mtrArea )
list_ad = a_with_d.toList(1000)
csv = open("result.csv", "a")
try:
    actual_list = list_ad.getInfo()
    for feat in actual_list:
        dist = feat['properties']['dist'] 
        area = feat['properties']['area'] 
        id_num = feat['properties']['FEATURE_ID'] 
        csvWrite(csv, id_num, dist, area)

except ee.ee_exception.EEException:
    missed = open("missed_counties.txt", "a")
    missed.write( county+"\n")
    missed.close()

finally:
    csv.close()
