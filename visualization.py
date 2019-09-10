import matplotlib.pyplot as plt

import pandas as pd
# don't show warning
pd.set_option('mode.chained_assignment', None)


def draw(data, ylabel=None, filter={}, ifshow=False):

    if ylabel == None:
        # use the column named *Volume as ylabel
        for col in data.columns:
            if 'Volume' in col:
                ylabel = col
                break

    # filter
    label = ''
    for key, value in filter.items():
        data = data[data[key] == value]
        label += str(value)

    # new column called regDate
    data['regDate'] = data['regYear'] * 100 + data['regMonth']

    # sort according to regDate
    data.index = data['regDate']
    data = data.sort_index()

    # sum the data with same regDate
    data = data.groupby(data['regDate']).sum()

    # regDates are mapped to 1 ~ len(column)
    data.index = range(1, data.shape[0] + 1)

    plt.plot(data[ylabel], label=label)

    if ifshow:
        plt.show()


def show_all_salesVolume(col, ifshowlabel=False):

    # read data
    path = 'Train/train_sales_data.csv'
    with open(path, 'r') as f:
        data = pd.read_csv(f)

    for item in set(data[col]):
        draw(data.copy(), filter={col: item})

    plt.title('salesVolume of all {}s'.format(col))
    if ifshowlabel:
        plt.legend()
    plt.show()

