import avro
# from avro.datafile import DataFileReader, DataFileWriter
from avro.io import DatumReader, DatumWriter
from io import BytesIO
#参考： https://avro.apache.org/docs/++version++/specification/
import yaml
import json  
import os
# import os
from datetime import datetime, timedelta
# import struct
def encode_uint16_list(uint16_list):
    """
    将 uint16 类型的整数列表编码为 bytes 格式。
    
    :param uint16_list: 包含 uint16 整数的列表
    :return: 编码后的 bytes 数据
    """
    # 使用 'h' 格式字符表示 int16,H uint16类型
    format_string = f'{len(uint16_list)}H'
    # 打包成 bytes
    encoded_bytes = struct.pack(format_string, *uint16_list)
    return encoded_bytes

def decode_uint16_list(encoded_bytes):
    """
    将 bytes 格式的数据解码为 uint16 类型的整数列表。
    
    :param encoded_bytes: 编码后的 bytes 数据
    :return: 解码后的 uint16 整数列表
    """
    # 计算 uint16 的数量
    num_uint16 = len(encoded_bytes) // 2
    # 使用 'h' 格式字符表示 int16,H uint16类型
    format_string = f'{num_uint16}H'
    # 解包成 uint16 列表
    uint16_list = struct.unpack(format_string, encoded_bytes)
    return list(uint16_list)


def str2bytes_by_bpe(msg,sp):
    encoded_ids = sp.encode(msg, out_type=int)
    encoded_pieces = sp.encode(msg, out_type=str)
    print(msg,'=>',' '.join(encoded_pieces))
    encoded_bytes = encode_uint16_list(encoded_ids)
    return encoded_bytes

def bytes2str_by_bpe(encoded_bytes,sp):
    decoded_ids = decode_uint16_list(encoded_bytes)
    decoded_text = sp.decode(decoded_ids)
    return decoded_text

def str2id_by_bpe(msg,sp):
    encoded_ids = sp.encode(msg, out_type=int)
    encoded_pieces = sp.encode(msg, out_type=str)
    print(msg,'=>',' '.join(encoded_pieces))
    return encoded_ids

def id2str_by_bpe(encoded_ids,sp):
    decoded_text = sp.decode(encoded_ids)
    return decoded_text

def encode_by_json_serial(obj,schema):
    ''' 对一个obj进行编码，返回bytes
    '''
    if type(schema) == avro.schema.RecordSchema:
        out = BytesIO()
        dWrite =  DatumWriter(schema)
        binaryEncoder = avro.io.BinaryEncoder(out)
        dWrite.write(obj,binaryEncoder)
        out.seek(0)
        _bytes = out.getvalue()
    else: # asn1
        _bytes = schema.encode('VTEMsg', obj)
    return _bytes

def decode_by_json_serial(_bytes,schema):
    ''' 对一个bytes进行解码，返回obj
    '''
    if type(schema) == avro.schema.RecordSchema:
        _in = BytesIO(initial_bytes=_bytes)
        dRead =  DatumReader(schema)
        binaryEncoder = avro.io.BinaryDecoder(_in)
        obj = dRead.read(binaryEncoder)
    else: # asn1
        obj = schema.decode('VTEMsg', _bytes)
    return obj

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
def load_yaml(file_path):
      with open(file_path, 'r') as file:
        return yaml.safe_load(file)
# 由于avro.schema.RecordSchema.validate的日志不清楚，改用自己的方法
# 这叫monkey patching，一般情况下不建议使用,可能带来难以调试的风险
def validate(self, datum):
        """Return self if datum is a valid representation of this schema, else None"""
        # print('myvalidate=')
        if isinstance(datum, dict):
            fields = {f.name for f in self.fields}
            for k in datum.keys():
                if k not in fields:
                    print(f'datum field {k} not in fields {fields}')
                    return None
            return self
        return None
# import inspect
# print(avro.schema.RecordSchema.validate,inspect.getsource(avro.schema.RecordSchema.validate))
# avro.schema.RecordSchema.validate = validate
# print(avro.schema.RecordSchema.validate,inspect.getsource(avro.schema.RecordSchema.validate))

def change_avro_cfg(conf_obj,tokenization_fields,new_type='bytes'):
    for field in tokenization_fields:
        names = field.split('.')
        target = conf_obj
        for n in names:
            if n == '[]': #表示数组 
                # pass
                pre_target = target
                target =  target['items']
            else:
                fields_in_conf = target['fields']
                for  f in fields_in_conf:
                    if f['name'] == n:
                        target =f['type']
                        pre_target = f
                        break
        print(f'config field:{field} to {new_type},orig type:{target}')
        # 修改string为bytes类型
        if type(target)==str and target == 'string':
            if 'items' in pre_target:
                pre_target['items']=new_type
            else:
                pre_target['type']=new_type
        elif type(target)==list: # 修改union类型 ['null','string']
            target[target.index('string')]=new_type
        else:
            raise Exception(f'config field:{field} to bytes,orig type:{target}')
    return conf_obj 

def chang_obj_fields(obj,field_def_list,process_func,**kwargs):
    def convert_str_bytes(target,names,process_func):
        '''递归把str转换为bytes
        '''
        n = names[0]
        if  len(names) == 1: #表示数组 
            target[n]=process_func(target[n],**kwargs)
        elif names[1] =='[]': #表示数组 
            for i in range(len(target[n])):
                if type(target[n][i]) == dict:
                    convert_str_bytes(target[n][i],names[2:],process_func)
                else:
                    target[n][i] = process_func(target[n][i],**kwargs)
        else:
            convert_str_bytes(target[n],names[:],process_func)
            
    for field in field_def_list:
        names = field.split('.')
        convert_str_bytes(obj,names,process_func)

def get_date_offset2(end_date,start_date, type=0):
    '''计算时间的偏移量，即两个时间相差的天数，可根据需求转换十进制和十六进制
    '''
    offset = (datetime.strptime(end_date[:10], '%Y-%m-%d') - datetime.strptime(start_date[:10],'%Y-%m-%d')).days
    if type == 1:
        offset = format(offset, 'X')
    return offset


def get_date2(offset,start_date,  type=0):
    '''根据偏移 + 指定日期，还原日期
    '''
    if type == 1:
        offset = int(offset, 16)
    return (datetime.strptime(start_date[:10], '%Y-%m-%d') + timedelta(days=int(offset))).strftime('%Y-%m-%d')   

def count_fields(json_obj):
    """
    递归函数，用于统计 JSON 对象中的字段数量。
    
    :param json_obj: JSON 对象（可以是字典或列表）
    :return: 字段数量
    """
    if isinstance(json_obj, dict):
        # 如果是字典，直接统计键的数量
        return sum(count_fields(v) for v in json_obj.values())
    elif isinstance(json_obj, list):
        # 如果是列表，递归统计每个元素的字段数量
        return sum(count_fields(item) for item in json_obj)
    else:
        # 如果是其他类型（如字符串、数字等），不计数
        # print(json_obj)
        return 1

def count_fields_payload(json_obj):
    """
    递归函数，用于统计 JSON 对象中的字段数量。
    
    :param json_obj: JSON 对象（可以是字典或列表）
    :return: 字段数量
    """
    if isinstance(json_obj, dict):
        # 如果是字典，直接统计键的数量
        return sum(count_fields_payload(v) for v in json_obj.values())
    elif isinstance(json_obj, list):
        # 如果是列表，递归统计每个元素的字段数量
        return sum(count_fields_payload(item) for item in json_obj)
    else:
        return len(str(json_obj).encode('utf8'))

def compare_dicts(dict1, dict2, path=""):
    """
    递归比较两个字典的内容，并打印差异的字段名称和值。

    :param dict1: 第一个字典
    :param dict2: 第二个字典
    :param path: 当前路径（用于记录嵌套的键）
    """
    # 获取两个字典的所有键
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    # 找到只存在于第一个字典中的键
    for key in keys1 - keys2:
        print(f"Key {path + key} is in dict1 but not in dict2. Value: {dict1[key]}")

    # 找到只存在于第二个字典中的键
    for key in keys2 - keys1:
        print(f"Key {path + key} is in dict2 but not in dict1. Value: {dict2[key]}")

    # 逐个比较共同的键
    for key in keys1 & keys2:
        full_path = f"{path}{key}."

        # 如果值都是字典，则递归比较
        if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            compare_dicts(dict1[key], dict2[key], full_path)
        # 如果值是列表，则递归比较列表中的每个元素
        elif isinstance(dict1[key], list) and isinstance(dict2[key], list):
            compare_lists(dict1[key], dict2[key], full_path)
        # 如果值不同，则打印差异
        elif dict1[key] != dict2[key]:
            print(f"Key {full_path[:-1]} has different values. dict1: {dict1[key]},{type(dict1[key])}, dict2: {dict2[key]},{type(dict2[key])}")

def compare_lists(list1, list2, path):
    """
    递归比较两个列表的内容，并打印差异的字段名称和值。

    :param list1: 第一个列表
    :param list2: 第二个列表
    :param path: 当前路径（用于记录嵌套的键）
    """
    if len(list1) != len(list2):
        print(f"List at {path[:-1]} has different lengths. list1: {len(list1)}, list2: {len(list2)}")
        return

    for i, (item1, item2) in enumerate(zip(list1, list2)):
        full_path = f"{path}[{i}]."

        # 如果项是字典，则递归比较
        if isinstance(item1, dict) and isinstance(item2, dict):
            compare_dicts(item1, item2, full_path)
        # 如果项是列表，则递归比较
        elif isinstance(item1, list) and isinstance(item2, list):
            compare_lists(item1, item2, full_path)
        # 如果项不同，则打印差异
        elif item1 != item2:
            print(f"Item at {full_path[:-1]} has different values. list1: {item1}, list2: {item2}")

import numpy as np
def check_qr_seq(seq_list):
    '''检查是否缺少其他的二维码
       返回二维码的总个数，缺少第几个(从1计数)
    '''
    total = int(seq_list[0][0])
    slots = np.array([0]*total)
    for i in seq_list:
        slots[int(i[1])-1]=1
    lost_qr = np.where(slots!=1)[0]
    if len(lost_qr)==0:
        return total,[]
    else:
        return total,(lost_qr+1).tolist()


def extract_from_multi_qr_content(strlist):
    '''根据序号，把多个二维码的内容，合并为一个大的字符串
    '''
    seq_msg_dict={x[2]:x[10:] for x in strlist}
    sorted_msg = sorted(seq_msg_dict.items(), key = lambda kv:kv[0])   
    return [x[1] for x in sorted_msg]


import struct

def uint32_to_n_bytes(uint32_value,n):
    '''把unint32转换为n个字节
    '''
    # 使用 struct 打包为 3 个字节
    return struct.pack('>I', uint32_value)[4-n:]

def bytes_to_uint32(bytes_data):
    # 确保输入是 3 个字节
    if len(bytes_data) >4:
        raise ValueError("Input must be <= 4 bytes")
    while len(bytes_data)<4:
        # 在前面添加一个字节 0x00，使其凑成 4 个字节
        bytes_data = b'\x00' + bytes_data
    # 使用 struct 解包为 uint32
    return struct.unpack('>I', bytes_data)[0]


def write_qr2png(qr_list,dir_path,error_correction=1,prefix="",border=4):
    '''
    error_correction的定义跟常识不一致，L为1
    ERROR_CORRECT_L = 1
    ERROR_CORRECT_M = 0
    ERROR_CORRECT_Q = 3
    ERROR_CORRECT_H = 2
    '''
    import qrcode
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    for filename in os.listdir(dir_path):
        if filename.endswith('.png'):
          os.unlink(os.path.join(dir_path, filename))
    # 首先清楚fdir目录下的文件
    img_paths =[]
    for i, qr_code in enumerate(qr_list):
        # border = 4 if len(qr_code) < 500 else int(4*len(qr_code)/400)
        # box_size = 10 if len(qr_code) < 500 else int(10*len(qr_code)/400)
        # 转换为 Base64
        # import base64
        # base64_encoded = base64.b64encode(qr_code)
        # # 转换为字符串以便查看
        # base64_string = base64_encoded.decode('utf-8')
        # print(f"{i}Base64 编码：", base64_string)
        box_size = 40 # 图片大一点，这样放大时不会模糊
        qr = qrcode.QRCode(border=border, box_size=box_size, error_correction=error_correction)
        qr.add_data(qr_code, optimize=0)
        qr.make()
        img = qr.make_image()
        print('字符长度', len(qr_code), 'version', qr.version, qr.border, qr.box_size) # 二维码版本对应https://www.qrcode.com/zh/about/version.html
        filename = os.path.join(dir_path,f'{prefix}{len(qr_list):02d}_{i:02d}_{qr.version}.png')
        # 保存图像
        img.save(filename)
        img_paths.append(filename)
    return img_paths

if __name__ == "__main__":
    pass
    # schema_orig = avro.schema.parse(json.dumps(conf_obj))              
    # config_field_str_to_bytes(conf_obj,tokenization_fields)    
    # schema = avro.schema.parse(json.dumps(conf_obj))  
    # pass
    # with open(os.path.join(os.path.dirname(__file__),'vte_decode.json'), 'r') as file:
    #     obj= json.load(file)
    
    # encode_bytes_orig = encode_by_json_serial(obj,schema_orig)   
    # convert_tokenization(obj,tokenization_fields,str_token_bytes)
    # schema = avro.schema.parse(json.dumps(conf_obj))          
    # encode_bytes = encode_by_json_serial(obj,schema)       
    # print('encode_bytes_orig=',len(encode_bytes_orig),'encode_bytes=',len(encode_bytes))  
    # obj2 = decode_by_json_serial(encode_bytes,schema)
    # convert_tokenization(obj2,tokenization_fields,token_bytes_str)
    # print(json.dumps(obj2,indent=2,ensure_ascii=False))  
    
    # schema = avro.schema.parse(json.dumps(conf_obj))          
    # encode_bytes = encode_by_json_serial(obj,schema)       
    # print(len(encode_bytes))            
    # encode_bytes = encode_by_json_serial(obj,schema)
    # out_obj = decode_by_json_serial(encode_bytes,schema)
    # print('bytes',len(encode_bytes))
    # print('out json format:',len(json.dumps(out_obj)),out_obj)
    # yaml_str = yaml.dump(out_obj,encoding='utf-8',allow_unicode=True)
    # print('out yaml format:',len(yaml_str),yaml_str.decode('utf8'))
    a = {'a':1,'b':{'c':2,'d':3,'e':[4,5,'abcded']}}
    print(count_fields(a),len(a))
    
    
    
    