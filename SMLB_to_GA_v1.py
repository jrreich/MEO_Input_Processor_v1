import csv
import simplekml
import pandas as pd
from datetime import datetime
from datetime import timedelta

kml = simplekml.Kml()

df = pd.read_excel('USCG_drift_test\SLDMB_Positions_Times.xlsx', index_col = 'DataDate', parse_dates = True)

print df.head(5)
df.to_csv('USCG_drift_test\SLDMB_Position_Times.csv')

# get first time
print 'hi'
with open('USCG_drift_test\SLDMB_Position_Times.csv', 'rb') as csvfile:
        csvfile.next()
        filereader = csv.reader(csvfile)
        t1 = datetime.strptime(next(filereader)[0], '%Y-%m-%d %H:%M:%S')
        print t1
with open('USCG_drift_test\SLDMB_Position_Times.csv', 'rb') as csvfile:
        csvfile.next()
        filereader = csv.reader(csvfile)
        rows = sum(1 for row in filereader)       
        with open('USCG_drift_test\SLDMB_Position_Times.ga', 'w') as gafile:  
                gafile.write('stk.v.8.0\n')
                gafile.write('\tBEGIN GreatArc\n')
                gafile.write('\t\tMethod\t\t\tDetTimeAccFromVel\n')
                gafile.write('\t\tTimeOfFirstWaypoint\t1 Dec 2016  17:27:00\n')
                gafile.write('\t\tArcGranularity\t\t5.729577951308e-001\n')
                gafile.write('\t\tAltRef\t\t\tWGS84\n')
                gafile.write('\t\tArcGranularity\t\t5.729577951308e-001\n')
                gafile.write('\t\tAltInterpMethod\t\tEllipsoidHeight\n')
                gafile.write('\t\tNumberOfWaypoints\t'+ str(rows) +'\n')
                gafile.write('\t\tBEGIN Waypoints\n')
with open('USCG_drift_test\SLDMB_Position_Times.csv', 'rb') as csvfile:
        csvfile.next()
        filereader = csv.reader(csvfile)
        for row in filereader:
            with open('USCG_drift_test\SLDMB_Position_Times.ga', 'a') as gafile:  
                gafile.write('\t\t{:0>8.2f}'.format((datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')-t1).total_seconds()) + 
                    '\t{:3.6f}'.format(float(row[5])) + '\t{:3.6f}'.format(float(row[6])) + '\t0.0' + '\t0.0'+ '\t0.0' +'\n' )
with open('USCG_drift_test\SLDMB_Position_Times.ga', 'a') as gafile:  
    gafile.write('\t\tEND Waypoints\n')
    gafile.write('\tEND GreatArc\n') 
