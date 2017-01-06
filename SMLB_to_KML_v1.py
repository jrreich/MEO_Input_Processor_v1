import csv
import simplekml
import pandas as pd

kml = simplekml.Kml()

df = pd.read_excel('USCG_drift_test\SLDMB_Positions_Times.xlsx', index_col = 'DataDate', parse_dates = True)

print df.head(5)
df.to_csv('USCG_drift_test\SLDMB_Position_Times.csv')

with open('USCG_drift_test\SLDMB_Position_Times.csv', 'rb') as csvfile:
        csvfile.next()
        filereader = csv.reader(csvfile)
        fol_SLDMB = kml.newfolder(name='SLDMB Locations')
        for row in filereader:            
            pnt_SLDMB = fol_SLDMB.newpoint(coords=[(float(row[6]),float(row[5]))], 
                description = 'SLDMB Location \n\nTime of Solution = ' + row[0] + '\nFOM = ' + row[7] + '\nSST = ' +row[9] 
                )
            # name=str(row[0][11:19])
            print row[0][:10] + 'T' + row[0][11:19]
            pnt_SLDMB.timespan.begin = row[0][:10] + 'T' + row[0][11:19]
            pnt_SLDMB.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/pal4/icon53.png'
        kml.save('USCG_drift_test\SLDMB_Position_Times.kml')