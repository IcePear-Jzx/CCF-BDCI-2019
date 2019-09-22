import keras
from keras import layers
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import numpy as np
import os

os.environ['CUDA_VISIBLE_DEVICES'] = '7'

train_file = 'Train/train_extra_data.csv'
eval_file = 'Forecast/evaluation_public.csv'


def preprocess_train_data():
    df = pd.read_csv(train_file)
    train_list = []
    for model in df['model'].unique():
        for adcode in df['adcode'].unique():
            index = (df['model'] == model) & (df['adcode'] == adcode)
            train_list.append(df[['salesVolume', 'popularity', 'carCommentVolum', 'newsReplyVolum']][index].values)
    return np.array(train_list)
    


def my_rmse(y_true, y_pred):
    return (np.sum((y_true - y_pred)**2))**0.5


def build_lstm():
    lstm = keras.Sequential()
    lstm.add(layers.LSTM(32, input_dim=4, return_sequences=False))
    # lstm.add(layers.LSTM(32, activation='relu'))
    # lstm.add(layers.Dense(32, activation='sigmoid'))
    lstm.add(layers.Dense(1))
    lstm.compile(keras.optimizers.Adam(0.01), loss=keras.losses.mse, metrics=[my_rmse])
    return lstm


def main():
    x = preprocess_train_data()
    print('The shape of input data is ', x.shape)
    lstm = build_lstm()
    lstm.summary()

    # lstm.fit(x[:, :-2, :], x[:, -2, 0], batch_size=32, epochs=40, validation_split=0.1, verbose=1)
    for t in range(1, x.shape[1]-1):
        lstm.fit(x[:, :t, :], x[:, t, 0], batch_size=32, epochs=5, validation_split=0.1)
    print('rmse: %.3f'%lstm.evaluate(x[:, :-1, :], x[:, -1, 0])[1])


if __name__ == '__main__':
    main()