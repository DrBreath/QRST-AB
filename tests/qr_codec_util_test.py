# -*- coding: utf-8 -*-
# @Time    : 2020/6/15 10:22
# @Author  : nijian
import sys
import os
import unittest
pythonPath = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if pythonPath not in sys.path:
    sys.path.insert(0,pythonPath)
from qrst.qr_codec_util import *
from copy import deepcopy
class TestAPI(unittest.TestCase):
    def setUp(self):
        print("测试开始")

    def test_uint16(self):
        # 创建一个示例 uint16 列表
        example_list = [1, 142, 3, 65000, 5, 2006,1232]
        # 编码
        encoded_data = encode_uint16_list(example_list)
        print(f"Encoded data:{len(encoded_data)}  {encoded_data}")
        # 解码
        decoded_list = decode_uint16_list(encoded_data)
        print(f"Decoded list: {len(decoded_list)}  {decoded_list}")
        self.assertListEqual(example_list,decoded_list)
        
    def test_bpe(self):
        import sentencepiece as spm
        sp = spm.SentencePieceProcessor()
        sp.Load(os.path.join(os.path.dirname(__file__),"./example/tokenizer_bpe_12000.model"))
        msg = 'Estimation of glomerular filtration rate Cys'
        e_bytes = str2bytes_by_bpe(msg,sp)
        msg2 = bytes2str_by_bpe(e_bytes,sp)
        self.assertEqual(msg,msg2)
        
    def test_avro(self):
        with open(os.path.join(os.path.dirname(__file__),'./example/qr.codec.test.config.yml'), 'r') as file:
            avro_conf= yaml.safe_load(file)['avro_conf']
        schema = avro.schema.parse(json.dumps(avro_conf))
        with open(os.path.join(os.path.dirname(__file__),'example/sample_en.json'), 'r') as file:
            obj= json.load(file)
        for field in ['admissionTime','patientId']:
           obj.pop(field,None)
        decoded_bytes = encode_by_json_serial(obj,schema)
        print('encoded_bytes_len:',len(decoded_bytes),'json_len',len(json.dumps(obj)))
        out_obj = decode_by_json_serial(decoded_bytes,schema)
        # print(json.dumps(out_obj,indent=4,ensure_ascii=False))
        # print(json.dumps(obj,indent=4,ensure_ascii=False))
        self.assertDictEqual(obj,out_obj)
    
    def test_change_avro_config(self):    
        # 把字符串进行tokenization
        conf_json = load_yaml(os.path.join(os.path.dirname(__file__),'example/qr.codec.test.config.yml'))
        avro_conf= conf_json['avro_conf']
        tokenization_fields = conf_json['tokenization_fields']
        avro_conf2  = deepcopy(avro_conf)
        f1 = next((x for x in avro_conf['fields'] if x['name']=='emergencyDept'), None) 
        f2 = next((x for x in avro_conf2['fields'] if x['name']=='emergencyDept'), None) 
        self.assertEqual(f1,f2)
        change_avro_cfg(avro_conf2,tokenization_fields)
        f2 = next((x for x in avro_conf2['fields'] if x['name']=='emergencyDept'), None) 
        self.assertNotEqual(f1,f2)
        
    def test_change_obj_fields(self):       
        # 把字符串进行tokenization
        conf_json = load_yaml(os.path.join(os.path.dirname(__file__),'example/qr.codec.test.config.yml'))
        tokenization_fields = conf_json['tokenization_fields']
        with open(os.path.join(os.path.dirname(__file__),'example/sample_en.json'), 'r') as file:
            obj= json.load(file)
            
        def process_func(x):
            return 'changed!'
        chang_obj_fields(obj,tokenization_fields,process_func)
        self.assertEqual(obj['emergencyDept'],'changed!')
        self.assertEqual(obj['laboratoryList'][0]['examName'],'changed!') 
     
    def test_date_offset(self): 
        t1 = '2022-01-08'
        days = get_date_offset2(t1,'2022-01-02')       
        t2 = get_date2(days,'2022-01-02')
        self.assertEqual(t1,t2)
        
        conf_json = load_yaml(os.path.join(os.path.dirname(__file__),'example/qr.codec.test.config.yml'))
        datetime_fields = conf_json['datetime_fields']
        
        with open(os.path.join(os.path.dirname(__file__),'sample.json'), 'r') as file:
            obj= json.load(file)
        obj2 = deepcopy(obj)
        chang_obj_fields(obj2, datetime_fields, get_date_offset2,start_date = obj['admissionTime'])
        print(json.dumps(obj2,indent=2))
        chang_obj_fields(obj2, datetime_fields, get_date2,start_date = obj['admissionTime'])
        self.assertDictEqual(obj,obj2)
        
    def test_compare(self):
          # 示例使用
        dict1 = {
            "name": "Alice",
            "age": 30,
            "address": {
                "city": "New York",
                "zipcode": "10001"
            },
            "hobbies": ["reading", "swimming"],
            "friends": [
                {"name": "Bob", "age": 28},
                {"name": "Charlie", "age": 32}
            ]
        }

        dict2 = {
            "name": "Alice",
            "age": 30,
            "address": {
                "city": "New York",
                "zipcode": "10002"
            },
            "hobbies": ["reading", "dancing"],
            "friends": [
                {"name": "Bob", "age": 28},
                {"name": "David", "age": 35}
            ]
        }
        compare_dicts(dict1, dict2)
    def  test_unint_bytes(self):
        v = 255
        _bytes = uint32_to_n_bytes(v,1)
        self.assertEqual(len(_bytes),1)
        self.assertEqual(v,bytes_to_uint32(_bytes))
        print(len(_bytes),struct.pack('<I', v),_bytes,bytes_to_uint32(_bytes))
        v = 356
        _bytes = uint32_to_n_bytes(v,2)
        self.assertEqual(len(_bytes),2)
        self.assertEqual(v,bytes_to_uint32(_bytes))
        
    # def test_check_qr_seq(self):
    #     seq_list = [(1,0)]
    #     t, losts = check_qr_seq(seq_list)
    #     self.assertEqual(1,t)
    #     self.assertListEqual(losts,[])
    #     seq_list = [(2,0),(2,1)]
    #     t, losts = check_qr_seq(seq_list)
    #     self.assertEqual(2,t)
    #     self.assertListEqual(losts,[])
    #     seq_list = [(3,0)]
    #     t, losts = check_qr_seq(seq_list)
    #     self.assertEqual(3,t)
    #     self.assertListEqual(losts,[1,2])
               
if __name__ == "__main__":
  unittest.main(verbosity=2)