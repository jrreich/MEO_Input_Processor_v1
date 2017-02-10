import numpy as np
import pandas as pd
from itertools import repeat
import matplotlib.pyplot as plt
import math
import sys
import os
import xlrd
from datetime import datetime
import csv
import beacon_decode_v1 as bcn
import simplekml
import re

kml = simplekml.Kml()

pd.options.mode.chained_assignment = None # turn off SettingWithCopyWarning

def read_config_file(configfile,row_start,row_end,column_key):
    configdict = {}
    wb = xlrd.open_workbook(configfile)
    sh = wb.sheet_by_index(0)
    for i in range(row_start-1,row_end-1): 
        try: 
            cell_value = sh.cell(i,column_key).value
            cell_key = sh.cell(i,column_key-1).value
            configdict[cell_key] = cell_value
        except Exception:
            break
    return configdict

def haversine(x):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    for i in x:
        #print 'i = '
        #print type(i)
        #print i
        if i == None:
            #print i
            #print 'N/A'
            return None

    lat1, lon1, lat2, lon2 = map(np.radians, [x[0], x[1], x[2], x[3]])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    r = 6373 # Radius of earth in kilometers. Use 3956 for miles
    #print c*r         
    return c * r

def singleburst_loc(df, lat_GT, lon_GT, MEOLUT):
    df2 = df[(df.SourceId == MEOLUT)]
    if df2.empty: return df2

    df2['Lat_GT'],df2['Lon_GT'] = lat_GT, lon_GT
    df2['Error_GT'] = df2[['Latitude','Longitude', 'Lat_GT','Lon_GT']].apply(haversine, axis = 1)
    df2['Error_Enc'] = df2[['Latitude','Longitude','Enc_Lat','Enc_Lon']].apply(haversine, axis = 1)
    dfSB = df2.sort_values('TimeLast')
    dfSB = dfSB.drop(['Lat_GT','Lon_GT'],axis = 1)
    dfSB['timestart_diff'] = dfSB['TimeFirst'].shift(-1) - dfSB['TimeFirst']
    dfSB['TimeToMcc'] = dfSB.index - dfSB['TimeLast']
    dfSB['TimeToGenerate'] = dfSB.index - dfSB['TimeLast']
    dfSB = dfSB[dfSB.timestart_diff > pd.Timedelta(seconds = 5)]
    return dfSB

def multiburst_loc(df,lat_GT,lon_GT,MEOLUT, window_span):
    timefirst = df.TimeFirst.min()
    timelast = df.TimeLast.max()
    df2 = df[(df.SourceId == MEOLUT)]
    if df2.empty: return df2
    df2['Lat_GT'],df2['Lon_GT'] = lat_GT, lon_GT
    df2['Error_GT'] = df2[['Latitude','Longitude', 'Lat_GT','Lon_GT']].apply(haversine, axis = 1)
    df2['Error_Enc'] = df2[['Latitude','Longitude','Enc_Lat','Enc_Lon']].apply(haversine, axis = 1)

    ##df2 = df2.sort_values('TimeFirst')
    df3 = df2.drop(['Lat_GT','Lon_GT'],axis = 1)
    
    # Sorting and finding windows
    df3 = df3.sort_values('TimeLast') #Rethink how you do windows 12/9
    df3['timestart_diff'] = df3['TimeFirst'].shift(-1) - df3['TimeFirst']
    df3['timestart_diff2'] = df3['TimeFirst'].shift(-2) - df3['TimeFirst']
    df3['TimeToMcc'] = df3.index - df3['TimeLast']
    df3['TimeToGenerate'] = df3.index - df3['TimeLast']
    #print df3.iloc[180:240,:]
    df3['last_in_window'] = (df3.timestart_diff > pd.Timedelta(minutes = 9)) & (df3.timestart_diff2 > pd.Timedelta(minutes = 3))    
    print df3[['TimeFirst','timestart_diff','timestart_diff2','last_in_window']]
    df3 = df3[(df3.timestart_diff > pd.Timedelta(minutes = 9)) & (df3.timestart_diff2 > pd.Timedelta(minutes = 3))]
    
    return df3  

MEOLUTName ={3669:'Florida',3385:'Hawaii',3677:'Maryland'}
MEOList = [3669, 3385, 3677]
MEOLUTLoc = {3669:(25.617645, -80.383211),3385:(21.524390, -158.001273),
    3677:(38.999121, -76.853789)}

if len(sys.argv) > 1:
    configfile = sys.argv[1]
else:
    configfile = "MEOInput_Analysis_config.xlsm"
#reader = csv.reader(open(configfile,'r'))
print 'Reading configuration:'
print '   ' + os.getcwd() + '\\' + configfile

configdict = read_config_file(configfile,2,22,2) # Reading configfile for items in rows 2 - 22 right now - column B and C

Lat_GT = configdict['Lat_GT']
Long_GT = configdict['Long_GT']
Location = configdict['Location']    
MEOLUT = int(configdict['MEOLUT']) # could be a list 
XLSXfolder = str(configdict['XLSXfolder']) #not needed
InputXLSX = str(configdict['InputXLSX']) #not needed
BeaconID = str(configdict['BeaconID']) # will be a regex string see below
# beacon_re = re.compile(BeaconIn) need eventually if you want to do regex for beacon ID
TimeStart = datetime(*xlrd.xldate_as_tuple(configdict['TimeStart'],0))
TimeEnd = datetime(*xlrd.xldate_as_tuple(configdict['TimeEnd'],0))
CSVoutfolder = str(configdict['CSVoutfolder'])
csvoutfilename = '{}_{}_{:%Y-%m-%d-%H%M}_{:%Y-%m-%d-%H%M}.csv'.format(MEOLUT,BeaconID,TimeStart,TimeEnd)
KML_generate = configdict['KML_gen']
Single_Burst = configdict['Single_Burst']
Enc_Locations = configdict['Enc_Locations']
LEOGEO = configdict['LEOGEO']
LEOGEO_file = configdict['LEOGEO_file']

data_cols = ['DataType','BcnId15','BcnId30','SourceId','TimeFirst','TimeLast','Latitude',
    'Longitude','Altitude','NumBursts','NumPackets','DOP','ExpectedHorzError']

data_cols = [0,1,2,4,8,9,10,11,12,13,14,17,18,19,20,21,22,36,37,47]

print('\n\nImporting - ' + XLSXfolder +'\\' + InputXLSX)
df = pd.read_excel(XLSXfolder +'\\' + InputXLSX, index_col = 'TimeSolutionAdded', parse_cols =  data_cols) #parse_dates = True,
df['TimeFirst']=pd.to_datetime(df['TimeFirst'], errors = 'ignore') ### FIX THIS WHEN TimeFirst is already a datetime.time 12/9 
df['TimeLast']=pd.to_datetime(df['TimeLast'], errors = 'ignore')
df['TimeSolutionGenerated']=pd.to_datetime(df['TimeSolutionGenerated'], errors = 'ignore')
#df['TimeSolutionAdded']=pd.to_datetime(df['TimeSolutionAdded'])

#df['DataType'] = df['DataType']
#df.set_index(df['TimeSolutionAdded'],inplace = True)
#df = df.drop(['BcnId36','FbiasDev', 'FreqDrift','SitFunc','MsgNum','QualityIndicator','NumAntennas','Srr', \
    #'PositionConfFlag','SortId','SortType','Distance'], axis = 1) -- No longer needed if I just slice into sub table
#df.sort_values('TimeSolutionAdded').head()

df2 = df[['DataType','BcnId15','BcnId30','SourceId','TimeFirst','TimeLast','Latitude',
    'Longitude','Altitude','NumBursts','NumPackets','DOP','ExpectedHorzError']]
df2 = df2.sort_index().ix[TimeStart:TimeEnd]
df3 = df2[(df2.BcnId15 == BeaconID)]
dfSB = df3[(df3.DataType == 3)] 
dfMB = df3[(df3.DataType == 0)] 
if df3.empty: print "Data Frame is empty after filtering out Beacon ID = " + BeaconID

lat_fun = lambda hexin: bcn.beacon(hexin).lat
lon_fun = lambda hexin: bcn.beacon(hexin).lon
dfSB['Enc_Lat'] = dfSB['BcnId30'].apply(lat_fun)
dfSB['Enc_Lon'] = dfSB['BcnId30'].apply(lon_fun)
dfMB['Enc_Lat'] = dfMB['BcnId30'].apply(lat_fun)
dfMB['Enc_Lon'] = dfMB['BcnId30'].apply(lon_fun)

df_SBL = singleburst_loc(dfSB,Lat_GT,Long_GT,MEOLUT)
SBL = len(df_SBL)
df5 = df_SBL[df_SBL.Error_GT < 5] if not df_SBL.empty else df_SBL
df5_enc = df_SBL[df_SBL.Error_Enc < 5] if not df_SBL.empty else df_SBL
df10 = df_SBL[df_SBL.Error_GT < 10] if not df_SBL.empty else df_SBL
df10_enc = df_SBL[df_SBL.Error_Enc < 10] if not df_SBL.empty else df_SBL
df20_enc = df_SBL[df_SBL.Error_Enc < 20] if not df_SBL.empty else df_SBL

timefirst = df3.TimeFirst.min()
timelast = df3.TimeLast.max()
timediff = timelast - timefirst

print timefirst

SBL_5 = len(df5)
SBL_5_enc = len(df5_enc)
SBL_10 = len(df10)
SBL_10_enc = len(df10_enc)
SBL_20_enc = len(df20_enc)

error_SBL = df_SBL.Error_GT if not df_SBL.empty else df_SBL # not used currently

expected_bursts = int(timediff/pd.Timedelta(seconds = 50))
prob_SBL = float(SBL)/expected_bursts if expected_bursts != 0 else 0
prob_SBL_5 =float(SBL_5)/SBL if SBL !=0 else 0
prob_SBL_5_enc =float(SBL_5_enc)/SBL if SBL !=0 else 0
prob_SBL_10 = float(SBL_10)/SBL if SBL !=0 else 0
prob_SBL_10_enc = float(SBL_10_enc)/SBL if SBL !=0 else 0
prob_SBL_20_enc = float(SBL_20_enc)/SBL if SBL !=0 else 0

print 'Analysis of MEOLUT -> {} - {}'.format(MEOLUTName[MEOLUT],MEOLUT)
print '\n Beacon Ground Truth Location used = {}, {}'.format(Lat_GT,Long_GT)
print ' Distance from MEOLUT = {:.1f} km'.format(haversine([Lat_GT,Long_GT,MEOLUTLoc[MEOLUT][0],MEOLUTLoc[MEOLUT][1]]))
#print ' Distance from MEOLUT = {:.1f} km'.format(haversine([Lat_GT,Long_GT,MEOlat,MEOlon]))
print ' Time of first burst = {:%Y-%m-%d %H:%M:%S}'.format(timefirst)
print ' Time of Last burst = {:%Y-%m-%d %H:%M:%S}'.format(timelast)
print ' Time Span = {}'.format(timediff)

print '\nSINGLE BURST ANALYSIS'
print 'Expected single burst locations = {}'.format(expected_bursts)
print '\n'
print 'Number of single burst locations = {}'.format(SBL)
print 'Probability of single burst location = {:.2%}'.format(prob_SBL)
print '\n'
print 'Number of single burst locations within 5 km = {}'.format(SBL_5)
print 'Percent of single burst locations within 5 km = {:.2%}'.format(prob_SBL_5)
print 'Number of single burst locations within 5 km (vs Encoded Location) = {}'.format(SBL_5_enc)
print 'Percent of single burst locations within 5 km (vs Encoded Location) = {:.2%}'.format(prob_SBL_5_enc)
print '\n'
print 'Number of single burst locations within 10 km = {}'.format(SBL_10)
print 'Percent of single burst locations within 10 km = {:.2%}'.format(prob_SBL_10)
print 'Number of single burst locations within 10 km (vs Encoded Location) = {}'.format(SBL_10_enc)
print 'Percent of single burst locations within 10 km (vs Encoded Location) = {:.2%}'.format(prob_SBL_10_enc)
print '\n'
print 'Number of single burst locations within 20 km (vs Encoded Location) = {}'.format(SBL_20_enc)
print 'Percent of single burst locations within 20 km (vs Encoded Location) = {:.2%}'.format(prob_SBL_20_enc)

## Multi Burst (Windowed) Section
window_time = 20 #minutes - no longer used since now just look for change in TimeFirst
window_span = pd.Timedelta(minutes = window_time)
expected_windows = math.ceil(timediff/window_span)

#print df3.head(5)

df_MBL = multiburst_loc(dfMB, Lat_GT, Long_GT, MEOLUT, window_span)
df_MBL5 = df_MBL[df_MBL.Error_GT < 5] if not df_MBL.empty else df_MBL
df_MBL5_enc = df_MBL[df_MBL.Error_Enc < 5] if not df_MBL.empty else df_MBL
df_MBL10 = df_MBL[df_MBL.Error_GT < 10] if not df_MBL.empty else df_MBL
df_MBL10_enc = df_MBL[df_MBL.Error_Enc < 10] if not df_MBL.empty else df_MBL
df_MBL20_enc = df_MBL[df_MBL.Error_Enc < 20] if not df_MBL.empty else df_MBL

MBL = len(df_MBL)
MBL_5 = len(df_MBL5)
MBL_5_enc = len(df_MBL5_enc)
MBL_10 = len(df_MBL10)
MBL_10_enc = len(df_MBL10_enc)
MBL_20_enc = len(df_MBL20_enc)

error_MBL = df_MBL.Error_GT if not df_MBL.empty else df_MBL # not used currently

prob_MBL = float(MBL)/expected_windows if expected_windows != 0 else 0
prob_MBL_5 =float(MBL_5)/MBL if MBL !=0 else 0
prob_MBL_5_enc =float(MBL_5_enc)/MBL if MBL !=0 else 0
prob_MBL_10 = float(MBL_10)/MBL if MBL !=0 else 0
prob_MBL_10_enc = float(MBL_10_enc)/MBL if MBL !=0 else 0
prob_MBL_20_enc = float(MBL_20_enc)/MBL if MBL !=0 else 0

print '\n\nMULTIPLE BURST ANALYSIS'
print 'Multiple Burst (windowed) locations, Window = {}'.format(window_span)
print 'Expected number of windows = {}'.format(int(expected_windows))
print '\n'
print 'Number of windowed locations = {}'.format(MBL)
print 'Probability of windowed location = {:.2%}'.format(prob_MBL)
print '\n'
print 'Number of windowed locations within 5 km = {}'.format(MBL_5)
print 'Percent of windowed locations within 5 km = {:.2%}'.format(prob_MBL_5)
print 'Number of windowed locations within 5 km (vs Encoded Location) = {}'.format(MBL_5_enc)
print 'Percent of windowed locations within 5 km (vs Encoded Location) = {:.2%}'.format(prob_MBL_5_enc)
print '\n'
print 'Number of windowed locations within 10 km = {}'.format(MBL_10)
print 'Percent of windowed locations within 10 km = {:.2%}'.format(prob_MBL_10)
print 'Number of windowed locations within 10 km (vs Encoded Location) = {}'.format(MBL_10_enc)
print 'Percent of windowed locations within 10 km (vs Encoded Location) = {:.2%}'.format(prob_MBL_10_enc)
print '\n'
print 'Number of windowed locations within 20 km (vs Encoded Location) = {}'.format(MBL_20_enc)
print 'Percent of windowed locations within 20 km (vs Encoded Location) = {:.2%}'.format(prob_MBL_20_enc)

df_SBL.to_csv(CSVoutfolder + '\SBL'+csvoutfilename)
df_MBL.to_csv(CSVoutfolder + '\MBL'+csvoutfilename)

with open(CSVoutfolder + '\OUT' + csvoutfilename, 'wb') as csvfile:
    csvoutwriter = csv.writer(csvfile, delimiter=',',
                            quoting=csv.QUOTE_MINIMAL)
    csvoutwriter.writerow(['MEOLUT', MEOLUTName[MEOLUT]])
    csvoutwriter.writerow(['MEOLUT_ID', MEOLUT])
    csvoutwriter.writerow(['BeaconID',BeaconID])
    csvoutwriter.writerow(['Location',Location])
    csvoutwriter.writerow(['TimeStart',TimeStart])
    csvoutwriter.writerow(['TimeEnd',TimeEnd])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['Ground Truth Lat',Lat_GT])
    csvoutwriter.writerow(['Ground Truth Long',Long_GT])
    csvoutwriter.writerow(['Distance From MEOLUT','{:.2f}'.format(haversine([Lat_GT,Long_GT,MEOLUTLoc[MEOLUT][0],MEOLUTLoc[MEOLUT][1]]))])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['Time First Burst','{:%Y-%m-%d %H:%M:%S}'.format(timefirst)])    
    csvoutwriter.writerow(['Time Last Burst', '{:%Y-%m-%d %H:%M:%S}'.format(timelast)])
    csvoutwriter.writerow(['Time Span', timediff])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['SINGLE BURST LOCATIONS'])
    csvoutwriter.writerow(['ExpSBL',expected_bursts])
    csvoutwriter.writerow(['NumSBL',SBL])
    csvoutwriter.writerow(['ProbSBL','{:.2%}'.format(prob_SBL)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumSBL <5km', SBL_5])
    csvoutwriter.writerow(['% SBL <5km', '{:.2%}'.format(prob_SBL_5)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumSBL <10km', SBL_10])
    csvoutwriter.writerow(['% SBL <10km', '{:.2%}'.format(prob_SBL_10)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumSBL <5km (vs Enc)', SBL_5_enc])
    csvoutwriter.writerow(['% SBL <5km (vs Enc)', '{:.2%}'.format(prob_SBL_5_enc)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumSBL <10km (vs Enc)', SBL_10_enc])
    csvoutwriter.writerow(['% SBL <10km (vs Enc)', '{:.2%}'.format(prob_SBL_10_enc)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumSBL <20km (vs Enc)', SBL_20_enc])
    csvoutwriter.writerow(['% SBL <20km (vs Enc)', '{:.2%}'.format(prob_SBL_20_enc)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['MULTIPLE BURST LOCATIONS'])
    csvoutwriter.writerow(['Window Period', window_span])
    csvoutwriter.writerow(['ExpMBL',expected_windows])
    csvoutwriter.writerow(['NumMBL',MBL])
    csvoutwriter.writerow(['ProbMBL','{:.2%}'.format(prob_MBL)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumMBL <5km', MBL_5])
    csvoutwriter.writerow(['% MBL <5km', '{:.2%}'.format(prob_MBL_5)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumMBL <10km', MBL_10])
    csvoutwriter.writerow(['% MBL <10km','{:.2%}'.format(prob_MBL_10)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumMBL <5km (vs Enc)', MBL_5_enc])
    csvoutwriter.writerow(['% MBL <5km (vs Enc)', '{:.2%}'.format(prob_MBL_5_enc)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumMBL <10km (vs Enc)', MBL_10_enc])
    csvoutwriter.writerow(['% MBL <10km (vs Enc)','{:.2%}'.format(prob_MBL_10_enc)])
    csvoutwriter.writerow([])
    csvoutwriter.writerow(['NumMBL <20km (vs Enc)', MBL_20_enc])
    csvoutwriter.writerow(['% MBL <20km (vs Enc)','{:.2%}'.format(prob_MBL_20_enc)])

print '\nWrite KML? - ' + Single_Burst

if KML_generate == 'Y':
    print 'Write Single Burst Locations to KML? - ' + Single_Burst
    print 'Write Encoded Locations to KML? - ' + Enc_Locations
    print 'Write LEO bursts to KML? - ' + LEOGEO
    print '\nWriting KML file'
    if Single_Burst == 'Y':
        with open(CSVoutfolder + '\SBL' + csvoutfilename, 'rb') as csvfile:
            csvfile.next()
            filereader = csv.reader(csvfile)
            folSBL = kml.newfolder(name='Single Burst Locations - '+ str(MEOLUT))
            folEnc = kml.newfolder(name = 'Encoded Locations - '+ str(MEOLUT))
            for row in filereader:            
                pntSBL = folSBL.newpoint(coords=[(float(row[8]),float(row[7]),float(row[9]))], 
                    description = 'Single Burst Solution \nBeacon = ' + row[2] + '\n\nTimeSolutionAdded = ' + row[0] + '\nTimeFirst = ' +row[5] + '\nTimeLast = ' +row[6] + 
                    '\nMEOLUT = ' + row[4] + '\nGT_Error = ' + row[16] + '\nEnc_Error = ' + row[17] +
                    '\nNum of Bursts = ' + row[10] + '\nNum of Packets = ' +row[11] +'\nDOP = ' + row[12] + 
                    '\nEHE = ' + row[13]
                    )
                # name=str(row[0][11:19])
                pntSBL.timespan.begin = row[0][:10] + 'T' + row[0][11:19]
                pntSBL.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
    if Enc_Locations == 'Y':
        with open(CSVoutfolder + '\SBL' + csvoutfilename, 'rb') as csvfile:
            csvfile.next()
            filereader = csv.reader(csvfile)
            folEnc = kml.newfolder(name = 'Encoded Locations - '+ str(MEOLUT))                
            for row in filereader:
                if row[17] <> '':  
                    pntEnc = folEnc.newpoint(coords=[(float(row[15]),float(row[14]))], 
                        description = 'Encoded Location - Beacon = ' + row[2] + '\n\nTimeSolutionAdded = ' + row[0] + '\nLat,Long = (' + row[14] + ', ' +row[15] + ')'  
                        )
                    pntEnc.timespan.begin = row[0][:10] + 'T' + row[0][11:19]
                    pntEnc.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/pal5/icon52.png'
                    pntEnc.style.iconstyle.scale = 0.8
                    pntEnc.style.labelstyle.color = '00ff0000'  # Red
                #pnt.snippet.content = 'this is content'
                #print row[0],row[7],row[8]
    with open(CSVoutfolder + '\MBL' + csvoutfilename, 'rb') as csvfile:
        csvfile.next()
        filereader = csv.reader(csvfile)
        folMBL = kml.newfolder(name='Multi Burst Locations - '+ str(MEOLUT))
        for row in filereader:            
            pntMBL = folMBL.newpoint(coords=[(float(row[8]),float(row[7]),float(row[9]))], 
                description = 'Multi Burst Location - Beacon = ' + row[2] + '\n\nTimeSolutionAdded = ' + row[0] + '\nTimeFirst = ' +row[5] + '\nTimeLast = ' +row[6] + 
                '\nMEOLUT = ' + row[4] + '\nGT_Error = ' + row[16] + '\nEnc_Error = ' + row[17] + 
                '\nNum of Bursts = ' + row[10] + '\nNum of Packets = ' +row[11] +'\nDOP = ' + row[12] + 
                '\nEHE = ' + row[13]
                )
            pntMBL.timespan.begin = row[0][:10] + 'T' + row[0][11:19]
            pntMBL.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle_highlight.png'
            pntMBL.style.labelstyle.color = 'ff0000ff'  # Red
            #pnt.snippet.content = 'this is content'
            #print row[0],row[7],row[8]
    

    
if LEOGEO == 'Y':
    print 'Reading LEO file - ' + XLSXfolder +'\\' + LEOGEO_file
    df = pd.read_excel(XLSXfolder +'\\' + LEOGEO_file, index_col = 'AddTime') #, parse_dates = True)
    df = df[(df.BcnId15 == BeaconID)]
    if df.empty: 
        print(LEOGEO_file + 'did not contain any data that matched')    
    else:
        dfLEO = df[df.Orbit.notnull()]
        dfLEO_loc = dfLEO[dfLEO.A_Lat.notnull()]
        dfLEO_loc.to_csv(CSVoutfolder +'\\' + LEOGEO_file + '.csv')
        with open(CSVoutfolder +'\\' + LEOGEO_file + '.csv', 'rb') as csvfile:
            filereader = csv.reader(csvfile)
            csvfile.next()
            fol_LEO = kml.newfolder(name='LEO Locations - '+ str(MEOLUT))
            for row in filereader:            
                pnt_LEO = fol_LEO.newpoint(coords=[(float(row[22]),float(row[21]))], 
                    description = 'LEO Location \nBeacon = ' + row[15] + '\n\nA_Tca = ' + row[23] + '\nMCCTime = ' + row[0] + '\n\nLUT = ' + row[2] + '\nSat = ' + row[3] +
                    '\nOrbit = ' + str(int(float(row[4]))) + '\n\nNominal = ' + row[73] +  
                    '\nNum of Points = ' +row[18] + '\nA_Cta =' + row[24] + '\nA_prob = ' +row[17] + '\nSolId = ' + row[1]  
                    )   
                pnt_LEO.timespan.begin = row[0][:10] + 'T' + row[0][11:19]
                pnt_LEO.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/ylw-blank.png'
                #pnt_LEO.style.iconstyle.icon.href = 'file://C:/Users/Jesse/Documents/Programming/Python/MEO_Input_Processor/MEO_Input_Processor_v2_w_KML/icon35.png'
                pnt_LEO.style.iconstyle.scale = 0.7
                pnt_LEO.style.labelstyle.color = 'ffff0000'  # Red

kml.save(CSVoutfolder + '\KML_' + csvoutfilename + '.kml')
#plt.figure('{} - Single Burst Errors'.format(MEOLUTName[MEOLUT]))
#SBL_plot = error_SBL.plot(subplots = True)
#f, ax = plt.subplots()
#ax = 
#title('{} - Single Burst Errors'.format(MEOLUTName[MEOLUT]))

#error_MBL.plot()
#plt.title('{} - Windowed Errors'.format(MEOLUTName[MEOLUT]))
#plt.show()