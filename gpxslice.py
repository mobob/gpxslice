#!/usr/bin/python
# -*- coding: ascii -*-

__author__ = 'Bob Durie'
__copyright__ = 'Copyright 2019, GPX Slice'
__credits__ = ['{gcdist lifted from https://gist.github.com/dal/4416699}']
__version__ = '1.0'

import xml.etree.ElementTree as ET
import argparse
import collections
import math

# setup our distance calculation functions
Point = collections.namedtuple('Point', ['lat', 'lon'])
nauticalMilePerLat = 60.00721
nauticalMilePerLongitude = 60.10793
milesPerNauticalMile = 1.15078
mPerMile = 1.60934 * 1000.0

def gcDist(pt1, pt2):
    '''
    Caclulate great circle distance between two lat lons in miles.
    @param pt1: The first Point instance.
    @param pt2: The second Point instance.
    @return: Great circle distance between the two points in miles.
    '''
    yDistance = (pt2.lat - pt1.lat) * nauticalMilePerLat
    xDistance = (math.cos(math.radians(pt1.lat)) + math.cos(math.radians(pt2.lat))) \
                * (pt2.lon - pt1.lon) * (nauticalMilePerLongitude / 2.0)

    distance = math.sqrt( yDistance**2.0 + xDistance**2.0 )
    return distance * milesPerNauticalMile * mPerMile

def elemToPoint(elem):
    lat = elem.attrib['lat']
    lon = elem.attrib['lon']
    return Point(float(lat), float(lon))

def slice(sliceArgs):
    tree = ET.parse(sliceArgs.infile)
    root = tree.getroot()

    # parse our file that defines how we'd like to split it up
    lines = sliceArgs.legDistancesFile.read().strip().split('\n')
    # these are in km, so move them in to m
    legDistanceMarkers = [ (1000.0 * float(s)) for s in lines ]
    legDistances = []
    # i updated the way they're fed in from absolute leg distances to
    # distance into the total distance, so this just converts back
    # (this change made so its easier to adjust the end point of a leg
    # without messing up further legs)
    for i in range(len(legDistanceMarkers)):
        if i == 0:
            legDistances.append(legDistanceMarkers[i])
        else:
            legDistances.append(legDistanceMarkers[i] - legDistanceMarkers[i - 1])
    numLegs = len(legDistances)

    # main vars
    totalDistance = 0.0
    legDistance = 0.0
    legIndex = 0
    totalPoints = 0
    firstIteration = True

    # first thing, add in all our new legs
    legtrksegs = []
    for i in range(numLegs):
        newtrk = ET.SubElement(root, 'trk')
        name = ET.SubElement(newtrk, 'name')
        name.text = 'Leg ' + str(i + 1)
        trkseg = ET.SubElement(newtrk, 'trkseg')
        legtrksegs.append(trkseg)

    # Root is assumed to be gpx
    for trk in root:
        if trk.tag != "{http://www.topografix.com/GPX/1/1}trk":
            continue
        for trkchild in trk:
            if trkchild.tag == "{http://www.topografix.com/GPX/1/1}trkseg":
                for trkpt in trkchild:
                    if trkpt.tag != "{http://www.topografix.com/GPX/1/1}trkpt":
                        print("didn't find a point: " + trkpt.tag)
                        continue
                    try:
                        curPoint = elemToPoint(trkpt)
                    except:
                        print("not a point: " + str(trkpt))
                        exit(1)

                    # we're good, add this point to our current leg
                    legtrksegs[legIndex].append(trkpt)
                    totalPoints = totalPoints + 1
                    if firstIteration == False:
                        incrementalDistance = gcDist(lastPoint, curPoint)
                        totalDistance = totalDistance + incrementalDistance
                        legDistance = legDistance + incrementalDistance
                    if legIndex + 1 < numLegs and legDistance > legDistances[legIndex]:
                        legIndex = legIndex + 1
                        print("moving on to next leg: " + str(legIndex + 1) + ", last leg distance: " + str(legDistance))
                        legDistance = 0.0
                    lastPoint = curPoint
                    firstIteration = False
    print("Total Points: " + str(totalPoints))
    print("Legs with points vs legs provided: (" + str(legIndex + 1) + " / " + str(numLegs) + ")")
    print("Total Distance: " + str(totalDistance))
    tree.write(sliceArgs.outfile)

def createLegsFile(createlegsfileArgs):
    avgLength = createlegsfileArgs.totalDistance / createlegsfileArgs.numLegs
    with open(createlegsfileArgs.outfile, 'w') as outfile:
        for i in range(createlegsfileArgs.numLegs):
            outfile.write(str((i + 1) * avgLength) + "\n")

#
#
#

# Register our namespace so the output looks ok
ET.register_namespace('', "http://www.topografix.com/GPX/1/1")

# And parse all the args for our 2 sub commands
parser = argparse.ArgumentParser(description='Tools to help slice a GPX file')

subparsers = parser.add_subparsers(help='sub-command help')

sliceParser = subparsers.add_parser('slice', help='Slice a GPX file')
sliceParser.add_argument("infile", type=argparse.FileType('r'), help="GPX filename to process")
sliceParser.add_argument('legDistancesFile', type=argparse.FileType('r'), help='leg distances file name')
sliceParser.add_argument('outfile', help='output file name')
sliceParser.set_defaults(func=slice)

createlegsParser = subparsers.add_parser('createlegsfile', help='Create a file with leg distances')
createlegsParser.add_argument("totalDistance", help="The total distance of the route", type=float)
createlegsParser.add_argument("numLegs", help="The number of legs", type=int)
createlegsParser.add_argument('outfile', help='output file name')
createlegsParser.set_defaults(func=createLegsFile)

args = parser.parse_args()
args.func(args)
