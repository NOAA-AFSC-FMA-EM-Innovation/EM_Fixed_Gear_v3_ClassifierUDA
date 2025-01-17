from torch.utils.data import Dataset
import pandas as pd
import os
from PIL import Image
from IPython import embed
import numpy as np
from util import calculate_num_class_model0
from util import name_to_logit_model7, level_2_names_to_2_id, level_2_names_to_2_id_split
# import cv2
from tqdm import tqdm

def name_to_logit_model0(name, hierarchy_dict):
    # NUM_CLASSES = calculate_num_class_model0(hierarchy_dict)
    logits = None

    # name can be level-1 or level-2
    level_1 = np.array(list(hierarchy_dict.keys()))
    # label只标到 level-1，logit应该是dim=36的one hot vector
    if len(np.where(level_1 == name)[0]) != 0:
        # index = np.where(level_1 == name)[0][0]
        # logits[index] = 1
        return logits  # 如果是leve-1的label，则不用！

    else:  # label不是level-1。是level-2，logit只有一个数字
        index = 0
        for group_id, group_name in enumerate(level_1):

            if name in hierarchy_dict[group_name]:
                # logits[group_id] = 1
                index_ = np.where(np.array(hierarchy_dict[group_name]) == name)[0][0]
                logits=index + index_

            else:  # 如果不在当前list，则index+长度
                index += len(hierarchy_dict[group_name])

    return logits


def name_to_logit_model12(name, hierarchy_dict):
    logits = []

    # name can be level-1 or level-2
    level_1 = np.array(list(hierarchy_dict.keys()))
    # label只标到 level-1，logits应该是 只有一个数字
    if len(np.where(level_1 == name)[0]) != 0:
        index = np.where(level_1 == name)[0][0]
        logits.append(index)
        logits.append(-1) #each element in list of batch should be of equal size，所以没有level-2的Label的  用-1 替代

    else:  # label不是level-1。是level-2，logit因该有两个数字!!!

        for group_id, group_name in enumerate(level_1):

            if name in hierarchy_dict[group_name]:
                logits.append(group_id)
                index = np.where(np.array(hierarchy_dict[group_name]) == name)[0][0]
                logits.append(index)

                break



    return np.array(logits)  # array之后才能直接转成tensor




import torch
import numpy as np
from torch.utils.data import Sampler

# class BalancedBatchSampler(Sampler):
#     def __init__(self, dataset, n_classes, n_samples):
#         self.dataset = dataset
#         self.n_classes = n_classes
#         self.n_samples = n_samples
#
#         self.class_indices = {}
#         for idx, (img, label_all, label_split, img_name, id) in enumerate(self.dataset):
#             level_2_label = label_all[1]
#             if level_2_label not in self.class_indices:
#                 self.class_indices[level_2_label] = []
#             self.class_indices[level_2_label].append(idx)
#
#         for label, indices in self.class_indices.items():
#             np.random.shuffle(indices)
#
#     def __iter__(self):
#         batch = []
#         for _ in range(len(self.dataset) // (self.n_classes * self.n_samples)):
#             for label, indices in self.class_indices.items():
#                 batch.extend(indices[:self.n_samples])
#                 self.class_indices[label] = indices[self.n_samples:] + indices[:self.n_samples]
#
#         return iter(batch)
#
#     def __len__(self):
#         return len(self.dataset)


def calculate_sample_weight(n_classes, trainset):
    # Compute class frequencies and inverse weights
    class_counts = np.zeros(n_classes)
    for img, label_all, label_split, img_name, id in tqdm(trainset):
        level_2_label = label_all[1]
        class_counts[level_2_label] += 1

    class_weights = 1.0 / class_counts

    # Assign a weight to each sample in the dataset
    sample_weights = np.zeros(len(trainset))
    for idx, (img, label_all, label_split, img_name, id) in tqdm(enumerate(trainset)):
        level_2_label = label_all[1]
        sample_weights[idx] = class_weights[level_2_label]

    return class_weights



class BalancedBatchSampler(Sampler):
    def __init__(self, dataset, n_classes, n_samples):
        self.dataset = dataset
        self.n_classes = n_classes
        self.n_samples = n_samples

        self.class_indices = {}
        for idx, (img, label_all, label_split, img_name, id) in tqdm(enumerate(self.dataset)):
            level_2_label = label_all[1]
            if level_2_label not in self.class_indices:
                self.class_indices[level_2_label] = []
            self.class_indices[level_2_label].append(idx)



        self.batches = self._generate_batches()

    def _generate_batches(self):
        batches = []
        for _ in tqdm(range(len(self.dataset) // (self.n_classes * self.n_samples))):
            batch = []
            for label, indices in self.class_indices.items():
                np.random.shuffle(indices)
                batch.extend(indices[:self.n_samples])
            batches.append(batch)
        return batches

    def __iter__(self):
        return iter(np.random.permutation(self.batches).flatten())

    def __len__(self):
        return len(self.dataset)


class BalancedBatchSamplerPreSaved(BalancedBatchSampler):
    def __init__(self, dataset, n_classes, n_samples):
        self.dataset = dataset
        self.n_classes = n_classes
        self.n_samples = n_samples

        # Load the npz file
        loaded_data = np.load('class_indices.npz')
        # Convert the string keys back to integers and access the loaded data
        self.class_indices = {int(k): v for k, v in loaded_data.items()}

        self.batches = self._generate_batches()


from util import level_2_names
class Fish_Rail_Dataset(Dataset):
    """Custom Dataset for loading CelebA face images"""

    def __init__(self, csv_path, img_dir, transform=None, hierarchy=None):
        df = pd.read_csv(csv_path, low_memory=False)
        self.img_dir = img_dir
        self.csv_path = csv_path
        self.img_names = df['filename'].values
        self.ids = df['id'].values
        self.y = df['class'].values
        self.transform = transform
        self.hierarchy = hierarchy


    def __getitem__(self, index):
        # try:
        img = Image.open(os.path.join(self.img_dir,self.img_names[index]))
        # img = cv2.imread(os.path.join(self.img_dir,self.img_names[index]))
        # except:
        #     print(self.img_names[index])
        #     return None

        img_name = self.img_names[index]
        # print(img_name)
        id = self.ids[index]

        if self.transform is not None:
            img = self.transform(img)



        name = self.y[index]

        # 读进来的是names,不是数字
        # label = name_to_logit_model0(name, self.hierarchy)
        # label_split = name_to_logit_model12(name, self.hierarchy)
        # label_all = name_to_logit_model7(name, self.hierarchy)

        label_all = np.array(level_2_names_to_2_id[name])
        label_split = np.array(level_2_names_to_2_id_split[name])



        # print(name, label_all.shape)


        #model 0 跳过只有Level-1标注的data
        # while label ==None:
        #     index+=1
        #
        #     img = Image.open(os.path.join(self.img_dir, self.img_names[index]))
        #
        #     if self.transform is not None:
        #         img = self.transform(img)
        #
        #     name = self.y[index]
        #
        #     # 读进来的是names,不是数字
        #     label = name_to_logit_model0(name, self.hierarchy)
        #     # label = name_to_logit_model12(name, self.hierarchy)



        # return img, label_all, label_split, img_name, id

        return img, label_all, label_split, img_name, id


    def __len__(self):
        return self.y.shape[0]


class Fish_Rail_Tracking_Result(Dataset):
    """Only need tracking id, img for inference, but crop detected bbox"""

    def __init__(self, csv_path, img_dir, transform=None, crop=True, return_label = False, species_column='class'):
        df = pd.read_csv(csv_path)
        self.img_dir = img_dir
        self.csv_path = csv_path
        self.img_names = df['filename'].values
        self.ids = df['id'].values
        self.xmin = df['xmin'].values
        self.ymin = df['ymin'].values
        self.xmax = df['xmax'].values
        self.ymax = df['ymax'].values
        self.transform = transform
        self.crop=crop
        self.y = df[species_column].values
        self.return_label = return_label

    def __getitem__(self, index):
        img = Image.open(os.path.join(self.img_dir,self.img_names[index]))

        img_name = self.img_names[index]
        # print(img_name)
        id = self.ids[index]
        xmin = self.xmin[index]
        ymin = self.ymin[index]
        xmax = self.xmax[index]
        ymax = self.ymax[index]

        # print('img size: ', img.size)
        if self.crop:
            img = img.crop((xmin, ymin, xmax, ymax)) # xmin, ymin, xmax, ymax
        # img.show()
        # print('img size: ', img.size)

        if self.transform is not None:
            img = self.transform(img)

        if self.return_label:
            name = self.y[index]

            label_all = np.array(level_2_names_to_2_id[name])
            label_split = np.array(level_2_names_to_2_id_split[name])

            return img, label_all, label_split, img_name, id

        return img, img_name, id


    def __len__(self):
        return self.ids.shape[0]

