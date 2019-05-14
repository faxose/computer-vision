"""Visualize bounding boxes

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import skimage
import matplotlib.pyplot as plt
import argparse
import os
import layer_utils
import label_utils
import config

from skimage.io import imread
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D


def show_anchors(image,
                 feature_shape,
                 anchors,
                 maxiou_indexes=None,
                 maxiou_per_gt=None,
                 labels=None,
                 show_grids=False):
    image_height, image_width, _ = image.shape
    batch_size, feature_height, feature_width, _ = feature_shape

    fig, ax = plt.subplots(1)
    ax.imshow(image)
    if show_grids:
        grid_height = image_height // feature_height
        for i in range(feature_height):
            y = i * grid_height
            line = Line2D([0, image_width], [y, y])
            ax.add_line(line)

        grid_width = image_width // feature_width
        for i in range(feature_width):
            x = i * grid_width
            line = Line2D([x, x], [0, image_height])
            ax.add_line(line)

    # maxiou_indexes is (4, n_gt)
    for index in range(maxiou_indexes.shape[1]):
        i = maxiou_indexes[1][index]
        j = maxiou_indexes[2][index]
        k = maxiou_indexes[3][index]
        # color = label_utils.get_box_color()
        box = anchors[0][i][j][k] #batch, row, col, box
        # default anchor box format is xmin, xmax, ymin, ymax
        w = box[1] - box[0]
        h = box[3] - box[2]
        x = box[0]
        y = box[2]
        # Rectangle ((xmin, ymin), width, height) 
        rect = Rectangle((x, y),
                         w,
                         h,
                         linewidth=2,
                         edgecolor='y',
                         facecolor='none')
        ax.add_patch(rect)

        if maxiou_per_gt is not None and labels is not None:
            # maxiou_per_gt[index] is row w/ max iou
            iou = np.amax(maxiou_per_gt[index])
            # offset
            label = labels[index]

            category = int(label[4])
            class_name = label_utils.index2class(category)
            color = label_utils.get_box_color(category)
            bbox = dict(facecolor=color, color=color, alpha=1.0)
            ax.text(label[0],
                    label[2],
                    class_name,
                    color='w',
                    fontweight='bold',
                    bbox=bbox,
                    fontsize=8,
                    verticalalignment='top')
            dxmin = label[0] - box[0]
            dxmax = label[1] - box[1]
            dymin = label[2] - box[2]
            dymax = label[3] - box[3]
            print(index, ":", label[4], iou, dxmin, dxmax, dymin, dymax)

    if labels is None:
        plt.show()

    return fig, ax



def feature_boxes(image, index):
    shift = [4, 5, 6, 7, 8] # image div by 2**4 to 2**8
    feature_height = image.shape[0] >> shift[index]
    feature_width = image.shape[1] >> shift[index]
    feature_shape = (1, feature_height, feature_width, image.shape[-1])
    boxes = layer_utils.anchor_boxes(feature_shape,
                                     image.shape,
                                     index=index,
                                     is_K_tensor=False)
    return feature_shape, boxes


if __name__ == '__main__':
    data_path = 'dataset/udacity_driving_datasets'
    parser = argparse.ArgumentParser()
    help_ = "Image to visualize"
    parser.add_argument("--image",
                        default = '1479506174991516375.jpg',
                        help=help_)

    help_ = "Index of receptive field (0 to 3)"
    parser.add_argument("--index",
                        default=0,
                        type=int,
                        help=help_)

    help_ = "Show grids"
    parser.add_argument("--show_grids",
                        default=False,
                        action='store_true',
                        help=help_)

    parser.add_argument('--maxiou_indexes',
                        nargs='*',
                        help='<Required> Set flag')

    help_ = "Show labels"
    parser.add_argument("--show_labels",
                        default=False,
                        action='store_true',
                        help=help_)
    args = parser.parse_args()

    image_path = os.path.join(data_path, args.image)
    image = skimage.img_as_float(imread(image_path))

    maxiou_indexes = None
    ax = None
    if args.maxiou_indexes is not None:
        if len(args.maxiou_indexes) % 2 != 0:
            exit(0)
        maxiou_indexes = np.array(args.maxiou_indexes).astype(np.uint8)
        maxiou_indexes = np.reshape(maxiou_indexes, [4, -1])
 
        feature_shape, boxes = feature_boxes(image, args.index)
        _, ax = show_anchors(image,
                             feature_shape,
                             boxes,
                             maxiou_indexes=maxiou_indexes,
                             maxiou_per_gt=None,
                             labels=None,
                             show_grids=args.show_grids)
        exit(0)

    if args.show_labels:
        csv_path = os.path.join(config.params['data_path'],
                                config.params['train_labels'])
        dictionary = label_utils.build_label_dictionary(csv_path)
        labels = dictionary[args.image]

        # labels are made of bounding boxes and categories
        labels = np.array(labels)
        boxes = labels[:,0:-1]

        feature_shape, anchors = feature_boxes(image, args.index)
        anchors_ = anchors
        anchors_shape = anchors.shape[0:4]
        anchors = np.reshape(anchors, [-1, 4])
        print("GT labels shape ", labels.shape)
        print("GT boxes shape ", boxes.shape)
        print("Complete proposed anchors shape ", anchors_.shape)
        print("Proposed anchors shape ", anchors_shape)

        iou = layer_utils.iou(anchors, boxes)
        print("IOU shape:", iou.shape)
        maxiou_per_gt, maxiou_indexes = layer_utils.maxiou(iou,
                                                           anchors_shape)
        _, ax = show_anchors(image,
                             feature_shape,
                             anchors=anchors_,
                             maxiou_indexes=maxiou_indexes,
                             maxiou_per_gt=maxiou_per_gt,
                             labels=labels,
                             show_grids=False)
        label_utils.show_labels(image, labels, ax)
