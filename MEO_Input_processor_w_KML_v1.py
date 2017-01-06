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

#import re # need eventually if you want to do regex for beacon ID

pd.options.mode.chained_assignment = None # turn off SettingWithCopyWarning

def read_config_file(configfile,row_start,row_end,column_key):
    configdict = {}
    wb = xlrd.open_workbook(configfile)
    sh = wb.sheet_by_index(0)
    for i in range(row_start-1,row_end-1): # Only looking for items in rows 2 - 21 right now - column B and C
        try: 
            cell_value = sh.cell(i,column_key).value
            cell_key = sh.cell(i,column_key-1).value
            configdict[cell_key] = cell_value
        except Exception:
            break
    return configdict

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    r = 6373 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def singleburst_loc(df, lat_GT, long_GT, MEOLUT):
    df2 = df[(df.DataType == 3) & (df.SourceId == MEOLUT)]
    if df2.empty: return df2
    df2['LAT_rad'], df2['LON_rad'] = np.radians(df2['Latitude']), np.radians(df2['Longitude'])
    df2['LAT_e_rad'], df2['LON_e_rad'] = np.radians(df2['Enc_Lat']), np.radians(df2['Enc_Lon'])

    df2['dLON'] = df2['LON_rad'] - np.radians(long_GT)
    df2['dLON_e'] = df2['LON_rad'] - df2['LON_e_rad']
    
    df2['dLAT'] = df2['LAT_rad'] - np.radians(lat_GT)
    df2['dLAT_e'] = df2['LAT_rad'] - df2['LAT_e_rad']
    df2['Error_GT'] = 6373 * 2 * np.arcsin(np.sqrt(np.sin(df2['dLAT']/2)**2 + 
        np.cos(np.radians(Lat_GT)) * np.cos(df2['LAT_rad']) * np.sin(df2['dLON']/2)**2))
    
    df2['Error_Enc'] = 6373 * 2 * np.arcsin(np.sqrt(np.sin(df2['dLAT']/2)**2 + 
        np.cos(np.radians(df2['Enc_Lat'])) * np.cos(df2['LAT_rad']) * np.sin(df2['dLON_e']/2)**2))
    dfSB = df2.drop(['LAT_rad','LON_rad','LAT_e_rad','LON_e_rad','dLON','dLON_e','dLAT','dLAT_e',],axis=1)
    dfSB = dfSB.sort_values('TimeLast')
    print dfSB.head(15)
    dfSB['timestart_diff'] = dfSB['TimeFirst'].shift(-1) - dfSB['TimeFirst']
    dfSB['TimeToMcc'] = dfSB.index - dfSB['TimeLast']
    dfSB['TimeToGenerate'] = dfSB.index - dfSB['TimeLast']
    dfSB = dfSB[dfSB.timestart_diff > pd.Timedelta(seconds = 5)]
    return dfSB

def multiburst_loc(df,Lat_GT,Long_GT,MEOLUT, window_span):
    timefirst = df.TimeFirst.min()
    timelast = df.TimeLast.max()
    df2 = df[(df.DataType == 0) & (df.SourceId == MEOLUT)]
    if df2.empty: return df2
    df2['LAT_rad'], df2['LON_rad'] = np.radians(df2['Latitude']), np.radians(df2['Longitude'])
    df2['dLON'] = df2['LON_rad'] - np.radians(Long_GT)
    df2['dLAT'] = df2['LAT_rad'] - np.radians(Lat_GT)
    df2['Error_GT'] = 6373 * 2 * np.arcsin(np.sqrt(np.sin(df2['dLAT']/2)**2 + 
        np.cos(np.radians(Lat_GT)) * np.cos(df2['LAT_rad']) * np.sin(df2['dLON']/2)**2))
    df3 = df2.drop(['LAT_rad','LON_rad','dLON','dLAT'],axis=1)
    df3 = df3.sort_values('TimeLast')
    df3['timestart_diff'] = df3['TimeFirst'].shift(-1) - df3['TimeFirst']
    df3['TimeToMcc'] = df3.index - df3['TimeLast']
    df3['TimeToGenerate'] = df3.index - df3['TimeLast']
    df3 = df3[(df3.timestart_diff > pd.Timedelta(minutes = 5)) | (df3.timestart_diff.isnull())]
    #df_MBL = df3[(df3['new_window'] == 1)]
    #time1 = timefirst
    #time2 = time1 + window_span
    #df_MBL = pd.DataFrame()
    #while time1 < (timelast + window_span):
    #    df4 = df3.sort_index().ix[time1:time2]
    #    #print df4
    #    if pd.notnull(df4.NumBursts.max()):
    #        #print df4[df4.NumBursts == df4.NumBursts.max()]
    #        df_MBL = df_MBL.append(df4[df4.NumBursts == df4.NumBursts.max()])
    #    time1 = time2
    #    time2 = time2 + window_span
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

configdict = read_config_file(configfile,2,20,2)

Lat_GT = configdict['Lat_GT']
Long_GT = configdict['Long_GT']
Location = configdict['Location']    
MEOLUT = int(configdict['MEOLUT'])
XLSXfolder = str(configdict['XLSXfolder'])
InputXLSX = str(configdict['InputXLSX'])
BeaconID = str(configdict['BeaconID'])
# beacon_re = re.compile(BeaconIn) need eventually if you want to do regex for beacon ID
TimeStart = datetime(*xlrd.xldate_as_tuple(configdict['TimeStart'],0))
TimeEnd = datetime(*xlrd.xldate_as_tuple(configdict['TimeEnd'],0))
CSVoutfolder = str(configdict['CSVoutfolder'])
csvoutfilename = '{}_{}_{:%Y-%m-%d-%H%M}_{:%Y-%m-%d-%H%M}.csv'.format(MEOLUT,BeaconID,TimeStart,TimeEnd)

df = pd.read_excel(XLSXfolder +'\\' + InputXLSX, index_col = 'TimeSolutionAdded', parse_dates = True)
df['TimeFirst']=pd.to_datetime(df['TimeFirst'])
df['TimeLast']=pd.to_datetime(df['TimeLast'])
df['TimeSolutionGenerated']=pd.to_datetime(df['TimeSolutionGenerated'])
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
if df3.empty: print "Data Frame is empty"

lat_fun = lambda hexin: bcn.beacon(hexin).lat
lon_fun = lambda hexin: bcn.beacon(hexin).lon
df3['Enc_Lat'] = df3['BcnId30'].apply(lat_fun)
df3['Enc_Lon'] = df3['BcnId30'].apply(lon_fun)

#df3['enc_lon'] = bcn.beacon(str(df2['BcnId30'])).lon
print df3.head(15)
df_SBL = singleburst_loc(df3,Lat_GT,Long_GT,MEOLUT)
SBL = len(df_SBL)
df5 = df_SBL[df_SBL.Error_GT < 5] if not df_SBL.empty else df_SBL
df10 = df_SBL[df_SBL.Error_GT < 10] if not df_SBL.empty else df_SBL
timefirst = df3.TimeFirst.min()
timelast = df3.TimeLast.max()
timediff = timelast - timefirst


SBL_5 = len(df5)
SBL_10 = len(df10)
error_SBL = df_SBL.Error_GT if not df_SBL.empty else df_SBL
expected_bursts = int(timediff/pd.Timedelta(seconds = 50))
prob_SBL = float(SBL)/expected_bursts if expected_bursts != 0 else 0
prob_SBL_5 =float(SBL_5)/SBL if SBL !=0 else 0
prob_SBL_10 = float(SBL_10)/SBL if SBL !=0 else 0

print 'Analysis of MEOLUT -> {} - {}'.format(MEOLUTName[MEOLUT],MEOLUT)
print '\n Beacon Ground Truth Location used = {}, {}'.format(Lat_GT,Long_GT,MEOLUTLoc[MEOLUT])
print ' Distance from MEOLUT = {:.1f} km'.format(haversine(Lat_GT,Long_GT,*MEOLUTLoc[MEOLUT]))
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
print '\n'
print 'Number of single burst locations within 10 km = {}'.format(SBL_10)
print 'Percent of single burst locations within 10 km = {:.2%}'.format(prob_SBL_10)

## Multi Burst (Windowed) Section
window_time = 20 #minutes - no longer used since now just look for change in TimeFirst
window_span = pd.Timedelta(minutes = window_time)
expected_windows = math.ceil(timediff/window_span)

#print df3.head(5)

df_MBL = multiburst_loc(df3, Lat_GT, Long_GT, MEOLUT, window_span)
df_MBL5 = df_MBL[df_MBL.Error_GT < 5] if not df_MBL.empty else df_MBL
df_MBL10 = df_MBL[df_MBL.Error_GT < 10] if not df_MBL.empty else df_MBL

MBL = len(df_MBL)
MBL_5 = len(df_MBL5)
MBL_10 = len(df_MBL10)
error_MBL = df_MBL.Error_GT if not df_MBL.empty else df_MBL
prob_MBL = float(MBL)/expected_windows if expected_windows != 0 else 0
prob_MBL_5 =float(MBL_5)/MBL if MBL !=0 else 0
prob_MBL_10 = float(MBL_10)/MBL if MBL !=0 else 0


print '\n\nMULTIPLE BURST ANALYSIS'
print 'Multiple Burst (windowed) locations, Window = {}'.format(window_span)
print 'Expected number of windows = {}'.format(int(expected_windows))
print '\n'
print 'Number of windowed locations = {}'.format(MBL)
print 'Probability of windowed location = {:.2%}'.format(prob_MBL)
print '\n'
print 'Number of windowed locations within 5 km = {}'.format(MBL_5)
print 'Percent of windowed locations within 5 km = {:.2%}'.format(prob_MBL_5)
print '\n'
print 'Number of windowed locations within 10 km = {}'.format(MBL_10)
print 'Percent of windowed locations within 10 km = {:.2%}'.format(prob_MBL_10)

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
    csvoutwriter.writerow(['Distance From MEOLUT','{:.2f}'.format(haversine(Lat_GT,Long_GT,*MEOLUTLoc[MEOLUT]))])
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


#plt.figure('{} - Single Burst Errors'.format(MEOLUTName[MEOLUT]))
#SBL_plot = error_SBL.plot(subplots = True)
#f, ax = plt.subplots()
#ax = 
#title('{} - Single Burst Errors'.format(MEOLUTName[MEOLUT]))

#error_MBL.plot()
#plt.title('{} - Windowed Errors'.format(MEOLUTName[MEOLUT]))
#plt.show()


