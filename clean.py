import pandas as pd
import IDExtractor as ide


def run(file_name, pbar, filter=False):
    """
    数据清洗
    """
    print(filter)
    data = pd.read_csv(
        file_name, sep=';'
    )
    pbar.emit('10')
    print(data.columns)
    data['Timestamp'] = data.apply(lambda r: r['Timestamp'][0:-13], axis=1)
    pbar.emit('15')
    res = data[data.ValueID == 1]
    res.rename(columns={'RealValue': '1'}, inplace=True)
    res.drop(res.columns[[0, 3, 4]], axis=1, inplace=True)
    id_list = ide.get_used_id_list(ide.ID_name)
    res.set_index('Timestamp', inplace=True)
    pbar.emit('20')
    for i in range(2, 58):
        if str(i) not in id_list:
            continue
        if len(data[data.ValueID == i]) is 0:
            continue
        tmp_data = data[data.ValueID == i].iloc[:, 1:3].values
        tmp_data = pd.DataFrame(tmp_data, columns=['Timestamp', str(i)])
        tmp_data.set_index('Timestamp', inplace=True)
        # cur_num = len(res.columns)
        res = res.join(tmp_data, on='Timestamp', how='outer', sort='Timestamp')
        pbar.emit(str(int(20 + (i - 2) / 56 * 75)))
    delete_list = []
    res.reset_index(inplace=True)
    # delete datas with 0 feeding flow
    if filter:
        for id in res.index:
            l = id - 10
            r = id + 10
            if l < 0 or r >= len(res):
                delete_list.append(id)
                continue
            min_num = 1e9
            for i in range(l, r):
                num = abs(float(res.loc[i, '16']))
                min_num = min(min_num, num)
            if min_num < 20:
                delete_list.append(id)

    new_data = res.drop(delete_list)
    print("size of the original :" + str(len(res)))
    print("size of result :" + str(len(new_data)))
    return new_data
