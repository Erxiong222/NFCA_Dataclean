import pandas as pd
import os

ID_name = "IDtoName.xls"


def get_used_id_list(file_name):
    id_table = pd.read_excel(file_name, sheet_name='Sheet1')
    no_used_list = ['不要', '不管', '没用', '没数据']
    res = []
    for rowid in id_table.index:
        row = id_table.loc[rowid]
        sym = True
        for no_used_str in no_used_list:
            if str(row.values[1]).find(no_used_str) is not -1:
                sym = False
        if sym is False:
            continue
        res.append(str(row['Index']))
    return res
