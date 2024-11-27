from qrst import QR_Codec,write_qr2png,load_json
import json
qr_codec = QR_Codec('./tests/example/qr.codec.test.config.yml')

# Input JSON: Read a JSON file
obj = load_json('./tests/example/sample_en.json')
# Encode into different QR code data streams
qr_list = qr_codec.encode(obj)
# Decode and restore it back to JSON
patient_id = obj.pop(qr_codec.conf['identity_field'] )
for qr_bytes in qr_list:
   flag,ret = qr_codec.decode(qr_bytes,patient_id)
   print('flag=',flag)
   if flag == 'finished':
      print('ret=',ret)
  
# Test generating QR code images
write_qr2png(qr_list,'./temp')

# Calculate compression ratio
orig_size = len(json.dumps(obj).encode())
compressed_size = sum([len(q) for q in qr_list])
print(f'JSON file size = {orig_size}bytes, compressed siez = {compressed_size}bytes,Compressed Ratio={orig_size/compressed_size:.2f}')