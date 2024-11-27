import sys
import os
import unittest
pythonPath = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if pythonPath not in sys.path:
    sys.path.insert(0,pythonPath)
from qrst.qr_code import *
from qrst.qr_codec_util import *
json_file = os.path.join(os.path.dirname(__file__),'example/sample_en.json')
conf_file = os.path.join(os.path.dirname(__file__),'example/qr.codec.test.config.yml')
class TestAPI(unittest.TestCase):
    def setUp(self):
        print("测试开始")

    def test_0_codec_body_avro(self):
        qr =  QR_Codec(conf_file,'avro')
        # qr.codec_type='avro'
        obj  = load_json(json_file)
        start_date = obj['admissionTime']
        obj.pop('admissionTime',None)
        obj.pop('patientId',None)
        stat={}
        obj1 = deepcopy(obj)
        bytes1 = qr.encode_body(obj,start_date,stat)
        obj2 = qr.decode_body(bytes1,start_date)
        print(stat)
        print(compare_dicts(obj2,obj1))
        self.assertDictEqual(obj2,obj1)
    
    def ttest_1_codec_body_asn1(self):
        qr =  QR_Codec(conf_file,'asn1')
        # qr.codec_type='avro'
        obj  = load_json(json_file)
        start_date = obj['admissionTime']
        obj.pop('admissionTime',None)
        obj.pop('patientId',None)
        stat={}
        obj1 = deepcopy(obj)
        bytes1 = qr.encode_body(obj,start_date,stat)
        obj2 = qr.decode_body(bytes1,start_date)
        print(stat)
        print(compare_dicts(obj2,obj1))
        self.assertDictEqual(obj2,obj1)
      
    def ttest_1_codec_(self):
        qr =  QR_Codec(conf_file,'avro')
        qr.max_qr_len=300
        # 多个二维码的场景
        obj  = load_json(json_file)
        stat = {}
        qr_list = qr.encode(obj,stat)
        # print(len(qr_list),stat)
        identity_id = obj[qr.conf['identity_field']]
        flag, r = qr.decode(b'1' + qr_list[0],identity_id)
        self.assertEqual(flag,'tag_error')
        flag, r = qr.decode(qr_list[0],identity_id+'x')
        self.assertEqual(flag,'auth_failed')
        flag, r = qr.decode(qr_list[0],identity_id)
        self.assertEqual(flag,'waiting')
        self.assertEqual(r,(2, 0, [1]))
        flag, r = qr.decode(qr_list[0],identity_id)
        self.assertEqual(flag,'duplicated')
        for qr_bytes in qr_list:
           flag, r = qr.decode(qr_bytes,identity_id)
        self.assertEqual(flag,'finished')
        self.assertDictEqual(obj,r)
        
        for qr_bytes in qr_list:
           flag, r = qr.decode(qr_bytes+b'1234',identity_id)
        self.assertEqual(flag,'exception')
        print(r)
        
        qr = QR_Codec(conf_file,'avro')
        qr.max_len = 20000
        # 一个二维码的场景
        qr_list = qr.encode(obj)
        identity_id = obj[qr.conf['identity_field']]
        flag, r = qr.decode( qr_list[0],identity_id)
        self.assertEqual(flag,'finished')
        self.assertDictEqual(obj,r)
        # count_seqs = []
        # for qr_bytes in qr_list:
        #   flag, r = qr.check_qr(qr_bytes,identity_id)
        #   self.assertTrue(flag)
        #   print('check_qr',flag)
        #   if flag:
        #     transaction_str,count,seq,z_bytes = r
        #     count_seqs.append((count,seq,z_bytes))
        #   else:
        #     continue
        # is_ok, tips = check_qr_seq(count_seqs)
        # print('is_ok, tips',is_ok, tips)
        # if is_ok:
        #     # 按序号排序
        #     sorted(count_seqs, key = lambda kv:kv[1])   
        #     merged_bytes = b''.join([i[2] for i in count_seqs])
        #     # 
        #     obj2 = qr.decode_body(merged_bytes,transaction_str) 
        #     obj2[qr.conf['transaction_field']]=transaction_str
        #     obj2[qr.conf['identity_field']]=identity_id
    def ttest_3_qr_write(self):
        qr =  QR_Codec(conf_file,'avro')
        # 多个二维码的场景
        obj  = load_json(json_file)
        qr_list = qr.encode(obj)
        dir_path = os.path.join(os.path.dirname(__file__),'temp')
        write_qr2png(qr_list,dir_path,error_correction=0)
        # dir_path = os.path.join(os.path.dirname(__file__),'temp',prefix='lever_M_')
        # write_qr2png(qr_list,dir_path,error_correction=0)
        
if __name__ == "__main__":
  # with open(os.path.join(os.path.dirname(__file__),'../../qr_codec/example/qr.codec.vte.config.yml'), 'r') as file:
  #     conf_obj= yaml.safe_load(file)
  unittest.main(verbosity=2)