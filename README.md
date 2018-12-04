# gps
Pure python script to get a gps fix on SailfishOS phones. Can be used standalone or as a importable class.

May also enable positioning if disabled in UI, but this needs prior setup of `sudo`

### command line invocation and arguments

```
[nemo@Sailfish]$ ./gps.py --help
usage: gps.py [-h] [-t TIMEOUT] [-a ACCURACY]

optional arguments:
  -h, --help            show this help message and exit
  -t TIMEOUT, --timeout TIMEOUT
                        Maximum time (in seconds) the program will run, trying
                        to get a fix, to reach the requested accuracy or
                        collecting a track
  -a ACCURACY, --accuracy ACCURACY
                        requested accuracy, in meters
```

```
[nemo@Sailfish]$ python3 gps.py 
location enabled
gps enabled
Mozilla location service (agps) enabled
gps status: Unavailable
gps status: Acquiring
satellites used: 0; visible: 28
satellites used: 2; visible: 28
satellites used: 3; visible: 28
gps status: Available
new position: [47.53214128, 1.07622818, 109.0], precision 35.0
average position: [47.53214128, 1.07622818, 109.0, 35.0], precision 35.0
satellites used: 4; visible: 28
new position: [47.53213695, 1.07621242, 108.0], precision 22.0
average position: [47.53213817628437, 1.076216883335284, 108.28320655354007, 18.626004082642105], precision 18.626004082642105
new position: [47.53214012, 1.07626797, 109.0], precision 18.0
average position: [47.532139181354066, 1.076243299575342, 108.65385098411326, 12.943574610175748], precision 12.943574610175748
new position: [47.53212019, 2.16293615, 105.0], precision 16.0
average position: [47.53213166903655, 1.0762800279660507, 107.20851492851513, 10.063035049411571], precision 10.063035049411571
new position: [47.53212354, 1.07628995, 103.0], precision 14.0
average position: [47.53212889984024, 1.07628340795575, 105.77486360475933, 8.171191141296395], precision 8.171191141296395

Accuracy reached!

With a precision of 8m the phone is at
geo:47.53212889984024,1.07628340795575
https://www.openstreetmap.org/?mlat=47.53212889984024&mlon=1.07628340795575&zoom=15

```

If the phone is moving (above 2.5 km/h), it will record the track up to the timeout and print the list of coordinates.
