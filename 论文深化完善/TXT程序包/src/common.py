"""公共参数和文件接口。输入输出单位沿用论文；发生约束错误时直接报错。"""
from pathlib import Path
import json,hashlib,datetime as dt
from functools import lru_cache
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[1]
DT=1/6;T=144;SEED=20260910
DATES=pd.date_range('2025-01-01',periods=365)
METHODS=['mean','ma7','ma14','ma30','ewma','ridge']


def dump(obj,path):
    # 将NumPy标量转为JSON可序列化数值；UTF-8保存中文检查结果。
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf-8')


def time_label(t):
    # 输入10分钟时段索引，输出24小时制时间标签。
    return f'{t//6:02d}:{t%6*10:02d}'


def interval(t,end=None):return time_label(t)+'-'+time_label(t+1 if end is None else end)
    # 把左端及可选右端索引转换为区间标签。


def align_time(label):
    # 模板按区间左端匹配，末列解释为本日首时段；这是论文约定。
    # 原模板最后列统一解释为本日 00:00--00:10；其他列按左端精确匹配。
    left=str(label).split('-')[0].replace('+1','')
    h,m=map(int,left.split(':')[:2]); return (h*60+m)//10


def _minute(v):
    # 把Excel时间或次日标记转换为分钟索引。
    if isinstance(v,dt.time):return v.hour*60+v.minute
    s=str(v);return 1440 if '+1' in s else int(s.split(':')[0])*60+int(s.split(':')[1])
