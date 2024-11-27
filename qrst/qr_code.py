import sys
import os

pythonPath = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if pythonPath not in sys.path:
    sys.path.insert(0,pythonPath)

import sentencepiece as spm
from qrst.qr_codec_util import *
from copy import deepcopy
import math
import zlib

import hashlib
from qrst.buff_mgr import get_buffMgr

 
class QR_Codec:
    def __init__(self, conf_file:str = os.path.join(os.path.dirname(__file__),'qr.codec.conf.yml'),serial_spec='avro'):
      """通过一个配置文件初始化
      Args:
          conf (_type_): 配置文件路径或者dict
      """
      if type(conf_file)  == str:
        with open(conf_file, 'r', encoding="utf-8") as file:
          conf= yaml.safe_load(file)
        # 做包含相对路径，则改为绝对路径
        for k, v  in conf.items():
          if (k.endswith('conf') or k.endswith('path')) and type(v)==str and v.startswith('.'):
              conf[k] = os.path.join(os.path.dirname(conf_file),v)
              print(f'{k}={v}自动更新为绝对路径{conf[k]}')
      else: 
         conf = conf_file
      self.conf = conf
      self.header_conf = conf['header']
      # 检查长度定义：
      for k,v in self.header_conf.items():
        if k == 'count':
           if v%4 != 0:
             raise Exception(f'消息头长度定义,{k} 必须是4的倍数')
           continue
        if v%8 != 0:
             raise Exception(f'消息头长度定义,{k} 必须是8的倍数')
      self.header_len = (sum(self.header_conf.values())+self.header_conf['count'])//8
      self.max_qr_len = conf['max_qr_len'] 
      # self.max_qr_num = int(math.exp2(self.header_conf['count']))
      self.max_qr_num = int(2 ** self.header_conf['count'])
      self.version = conf['version']
      self.version_offset_date = conf['version_offset_date']
      # 加载语言模型
      if conf['tokenization_model_path']:
        sp = spm.SentencePieceProcessor()
        sp.Load(conf['tokenization_model_path'])  
        self.sp = sp
      else:
        self.sp = None
      self.datetime_fields=conf['datetime_fields']
      self.tokenization_fields=conf['tokenization_fields']
      self.transaction_field =  conf['transaction_field']
      # JSON序列化类型
      self.serial_spec = serial_spec
      if serial_spec == 'avro':
        # avro_conf 支持文件路径，也支持直接写入
        if type(conf['avro_conf']) == str:
          avro_conf = load_yaml(conf['avro_conf'])
        else:
          avro_conf = conf['avro_conf']
        self.schema_orig = avro.schema.parse(json.dumps(avro_conf))
        avro_conf2  = deepcopy(avro_conf)
        change_avro_cfg(avro_conf2,self.tokenization_fields)
        change_avro_cfg(avro_conf2,self.datetime_fields,'int')
        self.schema = avro.schema.parse(json.dumps(avro_conf2))
      elif serial_spec == 'asn1':
        import asn1tools
        self.schema = asn1tools.compile_files(conf['asn1_conf'], 'uper')
        self.schema_orig = asn1tools.compile_files(conf['asn1_orig_conf'], 'uper')
        
      self.buffMgr = get_buffMgr(conf.get('db_path',':memory:'),conf.get('expired_time',600))
        
    def encode(self,obj:dict,stat=None):
        _obj = deepcopy(obj)
        identity_id =  _obj.pop(self.conf['identity_field'])
        admission_date =  _obj.pop(self.conf['transaction_field'])
        z_bytes = self.encode_body(_obj,admission_date,stat)
        qr_list = self.add_header(identity_id, admission_date,z_bytes)
        return qr_list
  
    def decode_header(self,qr_bytes:bytes,identity_id:str,is_test=False):
        h = self.header_conf
        start = 0
        end = start + h['tag']//8
        version = bytes_to_uint32(qr_bytes[start:end])
        if version != self.version:
           return 'tag_error',f'版本不匹配 {version},expected {self.version}'
        start = end
        end = start + h['identity']//8
        if not is_test and end > start:
            hash = hashlib.blake2b(identity_id.encode(),digest_size=self.header_conf['identity']//8) 
            identity_hash_login  = hash.digest()   
            identity_hash_qr = qr_bytes[start:end]
            if identity_hash_login != identity_hash_qr:
              return 'auth_failed',f'二维码与登录用户的hash值不一致'
        # 提取 事务id
        start = end
        end = start + h['transaction']//8
        transaction_str = ""
        if end> start:
          transaction_str = get_date2(bytes_to_uint32(qr_bytes[start:end]),self.version_offset_date)
        start = end
        end = start + h['count']*2//8
        count_seq = bytes_to_uint32(qr_bytes[start:end])
        count,seq = count_seq//self.max_qr_num+1,count_seq%self.max_qr_num
        if count <= seq:
            return 'tag_error',f'版本不匹配 {version},expected {self.version}'
        z_bytes = qr_bytes[end:]
        # return True, (transaction_str,count,seq,z_bytes)
        ret = (transaction_str,count,seq,z_bytes)
        return None,ret

    def decode(self,qr_bytes:bytes,identity_id:str,is_test=False):
        """
        return  flag, ret:
                flag: 返回值有下面6种情况
                     finished: 二维码扫描成功，解码完成
                     waiting: 二维码扫描成功，请继续第[n,m,k...]个二维码
                     duplicated: 二维码重复扫描，请继续第[n,m,k...]个二维码
                     tag_error: 标签错误，不是程序支持的二维码格式
                     auth_failed: 鉴权失败，请确认是否已授权
                     exception: 其它异常，请联系技术支持获取帮助
                ret: 返回值，根据flag的值而定
                     finished: -> str
                     waiting: -> json
                     duplicated: -> json
                     tag_error: -> str
                     auth_failed -> str
                     exception: -> str
        """
        try:
          flag, ret = self.decode_header(qr_bytes,identity_id,is_test)
          if flag is not None:
            return flag, ret 
          transaction_str, rec = ret[0],ret[1:]
          # 在缓存中进行合并处理
          flag, ret = self.buffMgr.process_obj(identity_id,transaction_str,rec)
          if flag == 'finished':
            # 对合并后的消息体进行解码
            obj2 = self.decode_body(ret,transaction_str) 
            obj2[self.conf['transaction_field']]=transaction_str
            obj2[self.conf['identity_field']]=identity_id
            ret = obj2
          return flag, ret
        except Exception as e:

          return 'exception', str(e)

     
    def add_header(self,identity_id:str,transaction_id:str, body_bytes:bytes):
      '''对头部进行编码
      '''
      # 生成hash值 https://docs.python.org/3/library/hashlib.html#blake2
      hash = hashlib.blake2b(identity_id.encode(),digest_size=self.header_conf['identity']//8) 
      identity_hash  = hash.digest()   
      
      transaction_v = get_date_offset2(transaction_id,self.version_offset_date)
      num = math.ceil(len(body_bytes) / (self.max_qr_len-self.header_len))  # 需要几个二维码
      single_size = math.ceil(len(body_bytes) / num)  # 平均每个多大     
      # 计算需要多少个二维码
      qr_list = []
      for i in range(num):
        # count和seq共同组成一个数
        count_seq = (num-1)*self.max_qr_num + i
        result=[
          uint32_to_n_bytes(self.version,self.header_conf['tag']//8), # tag
          identity_hash,   # id
          uint32_to_n_bytes(transaction_v,self.header_conf['transaction']//8), 
          uint32_to_n_bytes(count_seq,self.header_conf['count']*2//8),  # count+seq
        ]
        result.append(body_bytes[i*single_size:i*single_size + single_size])
        qr_list.append(b''.join(result))
      return qr_list
    
    def encode_body(self, obj:dict,start_date:str,stat=None):
      """对一个obj对象进行编码，返回编码后的bytes
      1、时间预处理，改为相对天数
      2、tokenization处理
      3、avro编码
      4、gzip压缩
      Args:
          obj (dict): _description_
      """
      # 1、时间预处理，改为相对时间
      if stat is not None:
        stat['json']=len(json.dumps(obj,ensure_ascii=False).encode('utf8'))
        stat['fields']=count_fields(obj)
        stat['yaml']=len(yaml.dump(obj,allow_unicode=True).encode('utf8'))
        stat['json_z']=len(zlib.compress(json.dumps(obj,ensure_ascii=False).encode('utf8')))
        stat['yaml_z']=len(zlib.compress(yaml.dump(obj,allow_unicode=True).encode('utf8')))
        _bytes = encode_by_json_serial(obj,self.schema_orig)
        stat[f'{self.serial_spec}']=len(_bytes)
        stat[f'{self.serial_spec}_z']=len(zlib.compress(_bytes))
        
      chang_obj_fields(obj, self.datetime_fields, get_date_offset2,start_date = start_date)
      chang_obj_fields(obj,self.tokenization_fields,str2bytes_by_bpe,sp=self.sp)

      encoded_bytes = encode_by_json_serial(obj,self.schema)
      z_bytes =zlib.compress(encoded_bytes)
      if stat is not None:
        stat[f'{self.serial_spec}_bpe']=len(encoded_bytes)
        stat[f'{self.serial_spec}_bpe_z']=len(z_bytes)
      return z_bytes
      
    def decode_body(self, body_bytes:bytes, start_date:str):
      '''
      1、gzip解压缩
      2、avro解码
      3、tokenization处理
      4、相对时间改为
      '''
      unzip_bytes = zlib.decompress(body_bytes)
      obj = decode_by_json_serial(unzip_bytes,self.schema)
      chang_obj_fields(obj,self.tokenization_fields,bytes2str_by_bpe,sp=self.sp)
      chang_obj_fields(obj,self.datetime_fields, get_date2,start_date = start_date)
      return obj

class QR_Codec_MutliVersions:
    def __init__(self, conf_file:str = os.path.join(os.path.dirname(__file__),'qr.codec.conf.yml'),other_versions:list=[],serial_spec='avro'):
      '''支持多个版本的二维码
        编码时按着当前版本编码，
        解码时，可以支持当前和历史的指定版本
      '''
      self.qr_codec = QR_Codec(conf_file, serial_spec)
      self.all_decoders = [self.qr_codec ]+ [QR_Codec(i, serial_spec) for i in other_versions ]
      
    def encode(self,obj:dict,stat=None):
        return self.qr_codec.encode(obj,stat)
    
    def decode(self,qr_bytes:bytes,identity_id:str):
      for decoder in self.all_decoders:
        flag, ret =  decoder.decode(self,qr_bytes,identity_id)
        if flag == 'tag_error':
           continue
        return flag, ret
        

if __name__ == "__main__":
    image_path = f"../test/"
    config_path =  f"./example/qr.codec.excel.config.yml"
    # read_and_recover_json(image_path, config_path)