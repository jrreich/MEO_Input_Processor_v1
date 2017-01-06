import beacon_decode_v1 as bcn

bcn30 = '93CE33D0B2502AC1AFE2760283AE1B'
#bcn30 = '96EE40B7591AE9F860EAB7EEC62AC1'
bcn30 = '96EE40B7591AE9F860EAB7D24613A6'
#bcn30 = '96E62F724B7FDFFC2076F583E0FAA8'
bcn30 = '96EE40B7591A69FBA1CF370E802C5D'


bcn1 = bcn.beacon(bcn30)

print 'format code'
print bcn1.format
print '\nprotocol'
print bcn1.protocol_1
print '\ncountry code = '
print bcn1.country_code 
print '\ncountry code (int)'
print int(bcn1.country_code,2)

print '\nprotocol'
print bcn1.protocol_2

print '\nprotocol'
print bcn1.protocol

print '\n15 Hex ID'
print bcn1.bcnID15
#print len(bcn1.bcnID15)

print '\nLocation'
print 'N/S flag'
print bcn1.lat_NS
print 'lat degrees'
print bcn1.lat_deg
print 'lat degrees binary'
print bcn1.lat_deg_bin

print 'E/W flag'
print bcn1.lon_EW
print 'lon degrees'
print bcn1.lon_deg
print 'lon degrees bin'
print bcn1.lon_deg_bin

#print '\n fine lat sign'
#print bcn1.lat_fine_sign
#print 'fine lat min'
#print bcn1.lat_fine_delta_min
#print 'fine lat sec'
#print bcn1.lat_fine_delta_sec

#print '\n fin lon sign'
#print bcn1.lon_fine_sign
#print 'fine lon min'
#print bcn1.lon_fine_delta_min
#print 'fine lon sec'
#print bcn1.lon_fine_delta_sec
#print '\nself lat delta'
#print bcn1.lat_delta
print '\nlat'
print bcn1.lat
#print '\nself lon delta'
#print bcn1.lon_delta
print '\nlon'
print bcn1.lon
 




