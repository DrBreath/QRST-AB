# QRST-AB

QRST-AB or QRST is a  QR code-based secure transmission algorithm (QRST-AB) using Avro and Byte Pair Encoding (BPE).

# Installation

install by pip
```shell
pip install qrst
```

or install by source code
```shell
git clone https://github.com/DrBreath/QRST-AB
cd QRST-AB
python setup.py install 
```
# Get Start

The demonstration code for encoding and decoding with qrst is as follows:
```python
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
```

- the demo code see as : [./demo.py](./demo.py)
- the example of config see as : [./tests/example/qr.codec.test.config.yml](./tests/example/qr.codec.test.config.ym) 

- the example of test json file see as : [./tests/example/sample_en.json](./tests/example/sample_en.json) 

# Practical Suggestions:
- Refer to [./tests/example/qr.codec.test.config.yml](./tests/example/qr.codec.test.config.ym)  to define your own JSON configuration file and `Apache Avro Schema`
- Using a private corpus to train a tokenizer can achieve better compression performance and prevent third-party decoding. For training methods, refer to [sentencepiece](https://github.com/google/sentencepiece)

# LICENSE
Apache License 2.0

Copyright [2024] [Changzhen Li]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Additional Terms:
- This software is provided for academic, non-commercial use only.
- Any commercial use of this software requires prior written authorization from the author.