import keras
from keras import layers
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import numpy as np
import os
from dataparser import write_results
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

train_file = 'Train/train_extra_data.csv'
eval_file = 'Forecast/evaluation_public.csv'


def preprocess_train_data():
    df = pd.read_csv(train_file)
    models = list(set(df['model']))
    adcodes = list(set(df['adcode']))
    train_x_list = []
    train_y_list = []
    for model in df['model'].unique():
        for adcode in df['adcode'].unique():
            index = (df['model'] == model) & (df['adcode'] == adcode)
            train_x_list.append([models.index(model), adcodes.index(adcode)])
            train_y_list.append(df[['salesVolume']][index].values)
    return np.array(train_x_list), np.array(train_y_list)


def build_mlp(input_dim):
    model = layers.Input(shape=(1, ))
    adcode = layers.Input(shape=(1, ))
    model_embed = layers.Embedding(60, 12, embeddings_initializer='he_normal')(model)
    adcode_embed = layers.Embedding(22, 12, embeddings_initializer='he_normal')(adcode)
    model_embed = layers.Flatten()(model_embed)
    adcode_embed = layers.Flatten()(adcode_embed)
    model_dense = layers.Dense(32, activation='sigmoid', kernel_initializer='he_normal')(model_embed)
    adcode_dense = layers.Dense(32, activation='sigmoid', kernel_initializer='he_normal')(adcode_embed)

    dense = layers.Add()([model_dense, adcode_dense])

    dense = layers.Dense(32, activation='sigmoid', kernel_initializer='he_normal')(dense)
    output = layers.Dense(12)(dense)
    model = keras.Model([model, adcode], output)
    model.compile(keras.optimizers.Adam(0.01), loss=keras.losses.mse)
    return model


def my_metric(y_true, y_pred):
    return np.mean(np.abs(y_true - y_pred))


def get_score(y_true, y_pred):
    return 1 - np.sum(np.abs(y_pred-y_true)/y_true)/60


# def scale_fit(x):
#     assert x.shape[1] % 12 == 0
#     mu = np.zeros(shape=(12, ), dtype=np.float)
#     sigma = np.zeros(shape=(12, ), dtype=np.float)
#     for i in range(12):
#         mu[i] = np.mean(x[:, [i + 12 * j for j in range(x.shape[1]//12)]])
#         sigma[i] = np.std(x[:, [i + 12 * j for j in range(x.shape[1]//12)]])
#     return mu, sigma


# def scale_to(x, mu, sigma, month_range):
#     assert x.shape[1] == len(month_range)
#     xs = np.zeros_like(x, dtype=np.float)
#     for i in range(x.shape[1]):
#         xs[:, i] = (x[:, i] - mu[month_range[i]])/sigma[month_range[i]]
#     return xs


# def scale_back(xs, mu, sigma, month_range):
#     assert xs.shape[1] == len(month_range)
#     x = np.zeros_like(xs, dtype=np.float)
#     for i in range(xs.shape[1]):
#         x[:, i] = xs[:, i]*sigma[month_range[i]] + mu[month_range[i]]
#     return x


def scale_fit(x):
    mu = np.mean(x)
    sigma = np.std(x)
    return mu, sigma


def scale_to(x, mu, sigma, month_range):
    xs = (x - mu) / sigma
    return xs


def scale_back(xs, mu, sigma, month_range):
    x = xs * sigma + mu
    return x


def line_func(x, k, b):
    return k * x + b


def exp_func(x, lam, a, b):
    return a * lam * np.exp(-lam * (x + b))


def power_func(x, lam, a):
    return a * np.power(x + 1, 1/lam)


def smooth(x):
    tend_x = np.arange(5.5, 18.5, 1)
    base_x = np.arange(0, 36, 1)

    tend_y = []
    for i in range(13):
        tend_y.append(np.mean(x[:, i:12+i], axis=1))
    tend_y = np.array(tend_y).T

    base = np.zeros(shape=(1320, 36))
    base_lower = np.zeros(shape=(1320, 36))
    base_center = np.zeros(shape=(1320, 36))
    base_upper = np.zeros(shape=(1320, 36))
    for i in range(0,1320):
        k = (tend_y[i][12] - tend_y[i][0]) / 12
        b = tend_y[i][0] - k * 5.5
        base_y = line_func(base_x, k, b)
        base[i] = base_y[:]
        var = x[i][:24] - base_y[:24]
        lower = (var[:12].min() + var[12:].min()) / 2
        upper = (var[:12].max() + var[12:].max()) / 2
        # lower = (var[:4].min() + var[12:16].min()) / 2
        # upper = (var[:4].max() + var[12:16].max()) / 2
        show = False
        if k < 0:
            # para, _ = curve_fit(exp_func, tend_x, tend_y[i] + lower, p0=[1, 10000, 0], maxfev = 1000000)
            para, _ = curve_fit(exp_func, tend_x, tend_y[i] + lower / 2, p0=[1, 10000, 0], maxfev = 1000000)
            lam = para[0]
            a = para[1]
            b = para[2]
            base_lower[i] = exp_func(base_x, lam, a, b)
            # base_upper[i] = base_lower[i] - lower + upper
            base_upper[i] = base_lower[i] - lower / 2 + upper
        elif k > 1:
            # para, _ = curve_fit(power_func, tend_x, tend_y[i] + upper, p0=[1, 200], maxfev = 1000000)
            para, _ = curve_fit(power_func, tend_x, tend_y[i] + upper / 2, p0=[1, 200], maxfev = 1000000)
            lam = para[0]
            if lam < 1:
                show = True
            a = para[1]
            base_upper[i] = power_func(base_x, lam, a)
            # base_lower[i] = base_upper[i] - upper + lower
            base_lower[i] = base_upper[i] - upper / 2 + lower
        else:
            para, _ = curve_fit(line_func, tend_x, tend_y[i], p0=[0, 200], maxfev = 1000000)
            k = para[0]
            b = para[1]
            base_center[i] = line_func(base_x, k, b)
            base_upper[i] = base_center[i] + upper / 2
            base_lower[i] = base_center[i] + lower
        
        # print('fit:', i)
        
        if show:
            plt.plot(range(24), x[i])
            plt.plot(tend_x, tend_y[i])
            plt.plot(base_x, base[i])
            plt.plot(base_x, base_upper[i])
            plt.plot(base_x, base_lower[i])
            plt.show()
    
    xs = x - base[:, :24]
    base_center = (base_lower + base_upper) / 2
    return xs, base, base_lower, base_center, base_upper


def main():
    x, y = preprocess_train_data()
    x = np.reshape(x, (-1, 2))
    y = np.reshape(y, (-1, 24))
    y, base, base_lower, base_center, base_upper = smooth(y)
    
    xs_train = np.vstack([x,x])

    mu, sigma = scale_fit(y)
    ys_train = scale_to(y[:, :12], mu, sigma, range(0, 12))
    ys_train = np.vstack([ys_train, scale_to(y[:, 12:], mu, sigma, range(0, 12))])

    print('The shape of input data is ', xs_train.shape, ys_train.shape)

    for i in range(10):
        model = build_mlp(input_dim=2)
        model.summary()

        model.fit([xs_train[:,:1],xs_train[:,1:]], ys_train, batch_size=32, epochs=300, validation_split=0, verbose=2)

        xs_eval = x
        ys_eval = model.predict([xs_eval[:,:1], xs_eval[:,1:]])
        y_eval = scale_back(ys_eval, mu, sigma, range(0, 12))
        # x = x + base[:, :24]
        y_eval = y_eval + base[:, 24:]

        # deal with long tail
        for j in range(1320):
            print('zoom:', j)
            upper = np.max(y_eval[j][:4])
            lower = np.min(y_eval[j][:4])
            center = base_center[j][24:28]
            upper_revise = base_upper[j][24:28]
            lower_revise = base_lower[j][24:28]
            zoom_upper = np.array([1,1,1,1])
            zoom_lower = np.array([1,1,1,1])
            if (lower < lower_revise).any():
                zoom_lower = (center - lower_revise) / (center - y_eval[j][:4])
            if (upper > upper_revise).any():
                zoom_upper = (center - upper_revise) / (center - y_eval[j][:4])
            zoom = np.vstack([zoom_lower, zoom_upper])
            zoom = zoom[zoom > 0].min()
            y_eval[j][:4] = center - (center - y_eval[j][:4]) * zoom

            # plt.plot(range(28), np.hstack([y[j] + base[j][:24], y_eval[j][:4]]))
            # plt.plot(range(28), base_center[j][:28])
            # plt.plot(range(28), base_lower[j][:28])
            # plt.plot(range(28), base_upper[j][:28])
            # plt.show()

        if y_eval[:, :4].min() < -0.1:
            print('Have negative number!')

        y_result = np.reshape(y_eval[:, :4], (1320*4), order='F')
        write_results('Results/mlp7-No.{}'.format(i), y_result)


if __name__ == '__main__':
    main()

