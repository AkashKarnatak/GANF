#%%
import os
import pandas as pd
import torch
from torch.utils.data import Dataset
import numpy as np

# %%
from torch.utils.data import DataLoader
def load_traffic(root, batch_size):
    """
    Load traffic dataset
    return train_loader, val_loader, test_loader
    """
    df = pd.read_hdf(root)
    df = df.reset_index()
    df = df.rename(columns={"index":"utc"})
    df["utc"] = pd.to_datetime(df["utc"], unit="s")
    df = df.set_index("utc")
    n_sensor = len(df.columns)

    mean = df.values.flatten().mean()
    std = df.values.flatten().std()

    df = (df - mean)/std
    df = df.sort_index()
    # split the dataset
    train_df = df.iloc[:int(0.75*len(df))]
    val_df = df.iloc[int(0.75*len(df)):int(0.875*len(df))]
    test_df = df.iloc[int(0.75*len(df)):]

    train_loader = DataLoader(Traffic(train_df), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(Traffic(val_df), batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(Traffic(test_df), batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader, n_sensor  

class Traffic(Dataset):
    def __init__(self, df, window_size=12, stride_size=1):
        super(Traffic, self).__init__()
        self.df = df
        self.window_size = window_size
        self.stride_size = stride_size

        self.data, self.idx, self.time = self.preprocess(df)
    
    def preprocess(self, df):

        start_idx = np.arange(0,len(df)-self.window_size,self.stride_size)
        end_idx = np.arange(self.window_size, len(df), self.stride_size)

        delat_time =  df.index[end_idx]-df.index[start_idx]
        idx_mask = delat_time==pd.Timedelta(5*self.window_size,unit='min')

        return df.values, start_idx[idx_mask], df.index[start_idx[idx_mask]]

    def __len__(self):

        length = len(self.idx)

        return length

    def __getitem__(self, index):
        #  N X K X L X D 
        start = self.idx[index]
        end = start + self.window_size
        data = self.data[start:end].reshape([self.window_size,-1, 1])

        return torch.FloatTensor(data).transpose(0,1)

def load_water(root, batch_size,label=False):
    
    data = pd.read_csv(root)
    data = data.rename(columns={"Normal/Attack":"label"})
    data.label[data.label!="Normal"]=1
    data.label[data.label=="Normal"]=0
    data["Timestamp"] = pd.to_datetime(data["Timestamp"])
    data = data.set_index("Timestamp")

    #%%
    feature = data.iloc[:,:51]
    mean_df = feature.mean(axis=0)
    std_df = feature.std(axis=0)

    norm_feature = (feature-mean_df)/std_df
    norm_feature = norm_feature.dropna(axis=1)
    n_sensor = len(norm_feature.columns)

    train_df = norm_feature.iloc[:int(0.6*len(data))]
    train_label = data.label.iloc[:int(0.6*len(data))]

    val_df = norm_feature.iloc[int(0.6*len(data)):int(0.8*len(data))]
    val_label = data.label.iloc[int(0.6*len(data)):int(0.8*len(data))]
    
    test_df = norm_feature.iloc[int(0.8*len(data)):]
    test_label = data.label.iloc[int(0.8*len(data)):]
    if label:
        train_loader = DataLoader(WaterLabel(train_df,train_label), batch_size=batch_size, shuffle=True)
    else:
        train_loader = DataLoader(Water(train_df,train_label), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(Water(val_df,val_label), batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(Water(test_df,test_label), batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader, n_sensor

class Water(Dataset):
    def __init__(self, df, label, window_size=60, stride_size=10):
        super(Water, self).__init__()
        self.df = df
        self.window_size = window_size
        self.stride_size = stride_size

        self.data, self.idx, self.label = self.preprocess(df,label)
    
    def preprocess(self, df, label):

        start_idx = np.arange(0,len(df)-self.window_size,self.stride_size)
        end_idx = np.arange(self.window_size, len(df), self.stride_size)

        delat_time =  df.index[end_idx]-df.index[start_idx]
        idx_mask = delat_time==pd.Timedelta(self.window_size,unit='s')

        return df.values, start_idx[idx_mask], label[start_idx[idx_mask]]

    def __len__(self):

        length = len(self.idx)

        return length

    def __getitem__(self, index):
        #  N X K X L X D 
        start = self.idx[index]
        end = start + self.window_size
        data = self.data[start:end].reshape([self.window_size,-1, 1])

        return torch.FloatTensor(data).transpose(0,1)


class WaterLabel(Dataset):
    def __init__(self, df, label, window_size=60, stride_size=10):
        super(WaterLabel, self).__init__()
        self.df = df
        self.window_size = window_size
        self.stride_size = stride_size

        self.data, self.idx, self.label = self.preprocess(df,label)
        self.label = 1.0-2*self.label 
    
    def preprocess(self, df, label):

        start_idx = np.arange(0,len(df)-self.window_size,self.stride_size)
        end_idx = np.arange(self.window_size, len(df), self.stride_size)

        delat_time =  df.index[end_idx]-df.index[start_idx]
        idx_mask = delat_time==pd.Timedelta(self.window_size,unit='s')

        return df.values, start_idx[idx_mask], label[start_idx[idx_mask]]

    def __len__(self):

        length = len(self.idx)

        return length

    def __getitem__(self, index):
        #  N X K X L X D 
        start = self.idx[index]
        end = start + self.window_size
        data = self.data[start:end].reshape([self.window_size,-1, 1])

        return torch.FloatTensor(data).transpose(0,1),self.label[index]


def load_drone(data_dir, batch_size, window_size=30):
    """
    Load drone dataset
    return train_loader, val_loader, test_loader
    """
    csv_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.csv')]

    def load_csv(csv_files, window_size=30):
        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            df = df.iloc[:df.shape[0] // window_size * window_size]
            df = (df - df.mean(axis=0)) / df.std(axis=0)
            dfs.append(df)
        return dfs

    train_csv_files = csv_files[:int(0.70*len(csv_files))]
    val_csv_files = csv_files[int(0.70*len(csv_files)):int(0.85*len(csv_files))]
    test_csv_files = csv_files[int(0.85*len(csv_files)):]

    np.random.shuffle(train_csv_files)
    np.random.shuffle(val_csv_files)
    np.random.shuffle(test_csv_files)

    train_dfs = load_csv(train_csv_files, window_size)
    val_dfs = load_csv(val_csv_files, window_size)
    test_dfs = load_csv(test_csv_files, window_size)

    n_attr = len(train_dfs[0].columns) - 1

    train_loader = DataLoader(Drone(train_dfs), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(Drone(val_dfs), batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(Drone(test_dfs), batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader, n_attr

class Drone(Dataset):
    def __init__(self, dfs, window_size=30, stride_size=5):
        super(Drone, self).__init__()
        self.window_size = window_size
        self.stride_size = stride_size

        self.data, self.idx = self.preprocess(dfs)

    def preprocess(self, dfs):
        idx, start = [], 0
        for df in dfs:
            idx.append(np.arange(start, start + len(df) - self.window_size, self.stride_size))
            start = len(df)
        idx = np.concatenate(idx)
        data = pd.concat(dfs).reset_index(drop=True)
        return data.values, idx

    def __len__(self):
        return len(self.idx)

    def __getitem__(self, index):
        #  N X K X L X D
        start = self.idx[index]
        end = start + self.window_size
        data = self.data[start:end].reshape([self.window_size,-1, 1])

        return torch.FloatTensor(data).transpose(0,1)
