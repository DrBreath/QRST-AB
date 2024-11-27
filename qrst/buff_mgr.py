import sqlite3
import numpy as np
import time
def check_qr_seq(seq_list):
    '''检查是否缺少其他的二维码
       返回二维码的总个数，缺少第几个(从1计数)
    '''
    # print(seq_list)
    total = int(seq_list[0][0])
    slots = np.array([0]*total)
    for i in seq_list:
        slots[int(i[1])]=1
    lost_qr = np.where(slots!=1)[0]
    return total,lost_qr.tolist()

class BuffMgr:
    def __init__(self, db_path:str = ":memory:",expired_time:int=3600):
        print('db_path',db_path)
        con = sqlite3.connect(db_path,isolation_level=None, check_same_thread=False)
        cur = con.cursor()
        # 自动清理过期数据，参考：https://cloud.tencent.com/developer/ask/sof/107895291
        trigger_sql = """
        CREATE TRIGGER Remove_Unactivated_qr_buf
        AFTER INSERT
        ON qr_buf
        FOR EACH ROW
        BEGIN
            DELETE FROM qr_buf
            WHERE activation_deadline <= strftime('%s', 'now');
        END;
        """
        try:
          cur.execute("CREATE TABLE qr_buf(id TEXT,transaction_id TEXT,count INTEGER,seq INTEGER,bytes BLOB, activation_deadline int)")
          print('创建表')
        except Exception as e:
          if 'already exists' in str(e):
            print('缓存表已存在')
          else:
            print('缓存表创建异常',type(e),e)
        try: 
          cur.execute(trigger_sql)
          print('创建触发器')
        except Exception as e:
          if 'already exists' in str(e):
            print('触发器已存在')
          else:
            print('触发器创建异常',type(e),e)
        self.cur = cur
        self.con = con
        self.expired_time = expired_time
        
    def __del__(self):
        # print("析构方法，对象被销毁的时候执行")
        self.cur.close()
        self.con.close()
        
    def process_obj(self,identity,transaction_id, r):
      if r[0] == 1:
        return 'finished',r[2]
      # 先查询之前的QR
      sql = f"SELECT count,seq,bytes FROM qr_buf WHERE id='{identity}' and transaction_id='{transaction_id}'"
      res = self.cur.execute(sql) 
      count_seqs = res.fetchall()
      if r[:2] in [x[:2]for x in count_seqs]:
         total, tips = check_qr_seq(count_seqs)
         return "duplicated",(total, r[1], tips)
         
      count_seqs.append(r)
      # 判断是否满足合并条件
      total, tips = check_qr_seq(count_seqs)
      if tips:
        # 若不满足，则保存obj
        data = {"id": identity,
          "transaction_id": transaction_id,
          "count":r[0],
          "seq":r[1],
          "bytes":r[2]
          }
        data["activation_deadline"] = int(time.time())+ self.expired_time
        self.cur.execute("INSERT INTO qr_buf VALUES(:id, :transaction_id,:count,:seq,:bytes,:activation_deadline)", data)
        return "waiting",(total, r[1], tips)
      else:
        self.cur.execute(f"DELETE FROM qr_buf WHERE id='{identity}' and transaction_id='{transaction_id}'")
        count_seqs.sort(key = lambda kv:kv[1])   
        merged_bytes = b''.join([i[2] for i in count_seqs])
        return 'finished', merged_bytes
      
buffMgr = None

def get_buffMgr(db_path,expired_time) -> BuffMgr:
    global buffMgr
    if buffMgr is None:
       buffMgr = BuffMgr(db_path,expired_time)
    return buffMgr
  
if __name__ == "__main__":
  bh  = BuffMgr(":memory:")
  identity = 'test'
  transaction_id = '124'
  status = []
  for i in  range(5):
    r = (3,i//2,b'123445')
    flag,ret = bh.process_obj(identity,transaction_id,r)
    print(flag)
    status.append(flag)

