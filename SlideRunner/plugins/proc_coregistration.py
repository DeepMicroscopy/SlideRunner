import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import openslide
import cv2
import numpy as np
import cv2, openslide
import numpy as np
import os, math
from scipy import ndimage
from scipy.stats import gaussian_kde
from skimage.color import rgb2lab
from sklearn.naive_bayes import GaussianNB
from sklearn import linear_model
import matplotlib.pyplot as plt
import logging

class TissueDetector:
    def __init__(self, name, threshold=0.5, training_files=""):
        self.name = name
        self.threshold = threshold
        self.tsv_name = training_files

    def read_training_dim(self, feature_dim):
        tsv_cols = np.loadtxt(self.tsv_name, delimiter="\t", skiprows=1)
        return tsv_cols[:, 0:feature_dim + 1]

    def get_gnb_model(self):
        if not os.path.exists(self.tsv_name):
            return self.get_default_gnb_model()
        else:
            bkg_train_data = self.read_training_dim(3)
            gnb_bkg = GaussianNB()
            gnb_bkg.fit(bkg_train_data[:, 1:], bkg_train_data[:, 0])
        return gnb_bkg

    def get_default_gnb_model(self):
        self.tsv_name = "./tissue_detection/tissue_others.tsv" # this file is created by our annotation tool
        bkg_train_data = self.read_training_dim(3)
        gnb_bkg = GaussianNB()
        gnb_bkg.fit(bkg_train_data[:, 1:], bkg_train_data[:, 0])
        return gnb_bkg

    def predict(self, wsi_thumb_img, open_operation=False):
        if self.name == "LAB_Threshold":
            lab_img = rgb2lab(wsi_thumb_img)
            l_img = lab_img[:, :, 0]
            # tissue is darker than background, recommend threshold value: 85
            binary_img_array_1 = np.array(0 < l_img)
            binary_img_array_2 = np.array(l_img < self.threshold)
            binary_img_array = np.logical_and(binary_img_array_1, binary_img_array_2) * 255
        elif self.name == "GNB":  # Gaussian Naive Bayes
            marked_thumbnail = np.array(wsi_thumb_img)
            gnb_model = self.get_gnb_model()
            cal = gnb_model.predict_proba(marked_thumbnail.reshape(-1, 3))
            cal = cal.reshape(marked_thumbnail.shape[0], marked_thumbnail.shape[1], 2)
            binary_img_array = cal[:, :, 1] > self.threshold
        else:
            raise Exception("Undefined model")
        if logging.DEBUG == logging.root.level:
            plt.imshow(binary_img_array)
            plt.show()
        if open_operation:
            binary_img_array = ndimage.binary_opening(binary_img_array, structure=np.ones((5, 5))).astype(
                binary_img_array.dtype)  # open operation
        return binary_img_array


class MatcherParameters:
    def __init__(self, layer_patch_num=None, layer_patch_max_try=None, layer_patch_size=None, rescale_rate=0):
        if rescale_rate == 0 or (layer_patch_num is None) or (layer_patch_max_try is None) or (layer_patch_size is None):
            self.rescale_rate = 100  # rescale to get the thumbnail
            self.layer_patch_num = [6, 6, 6]  # patch numbers per image level
            self.layer_patch_max_num = [20, 50, 50]  # maximum try at each image level
            self.layer_patch_size = [2000, 800, 500]  # patch size at each image level for registration
        else:
            self.rescale_rate = rescale_rate  # rescale to get the thumbnail
            self.layer_patch_num = layer_patch_num   # patch numbers per image level
            self.layer_patch_max_num = layer_patch_max_try  # maximum try at each image level
            self.layer_patch_size = layer_patch_size  # patch size at each image level for registration


class WSI_Matcher:
    def __init__(self, detector, parameters):
        self.tissue_detector = detector
        self.rescale_rate = parameters.rescale_rate  # rescale to get the thumbnail
        self.layer_patch_num = parameters.layer_patch_num  # patch numbers per image level
        self.layer_patch_max_num = parameters.layer_patch_max_num  # maximum try at each image level
        self.layer_patch_size = parameters.layer_patch_size  # patch size at each image level for registration

    @staticmethod
    def get_thumbnails(fixed_wsi_obj, float_wsi_obj, rescale_rate=100):
        fixed_wsi_w, fixed_wsi_h = fixed_wsi_obj.dimensions
        float_wsi_w, float_wsi_h = float_wsi_obj.dimensions
        thumb_size_x = fixed_wsi_w / rescale_rate
        thumb_size_y = fixed_wsi_h / rescale_rate
        thumbnail_fixed = fixed_wsi_obj.get_thumbnail([thumb_size_x, thumb_size_y]).convert("RGB")
        thumb_size_x = float_wsi_w / rescale_rate
        thumb_size_y = float_wsi_h / rescale_rate
        thumbnail_float = float_wsi_obj.get_thumbnail([thumb_size_x, thumb_size_y]).convert("RGB")
        return thumbnail_fixed, thumbnail_float

    @staticmethod
    def fast_reg(img_fixed, img_float, down_rate):  # patch registration
        fixed_img_array = np.array(img_fixed.convert("L")).astype(np.float32)
        float_img_array = np.array(img_float.convert("L")).astype(np.float32)
        c0, s0 = cv2.phaseCorrelate(fixed_img_array, float_img_array)
        xy_c = (c0[0]*down_rate, c0[1]*down_rate)
        return xy_c, s0

    # Getting a raw initial position on thumbnail
    @staticmethod
    def get_initial_pos(thumbnail_fixed, thumbnail_float, thumbnail_down_rate):
        brisk = cv2.BRISK_create()
        (kps_fixed, descs_fixed) = brisk.detectAndCompute(np.array(thumbnail_fixed), None)
        (kps_float, descs_float) = brisk.detectAndCompute(np.array(thumbnail_float), None)
        if (descs_fixed is None) or (descs_float is None):
            reg_status = 0
            init_reg_offset = (0, 0)
            return init_reg_offset, reg_status
        if len(kps_fixed) < 3 or len(kps_float) < 3:
            reg_status = 0
            init_reg_offset = (0, 0)
            return init_reg_offset, reg_status
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        try:
            matches = bf.match(descs_fixed, descs_float)
            matches = sorted(matches, key=lambda x: x.distance)
            if len(matches) < 3:  # less than 3 points
                reg_status = 0
                init_reg_offset = (0, 0)
                return init_reg_offset, reg_status
            if len(matches) <= 10:  # get first 10 points
                selected_matches = matches
            else:
                selected_matches = matches[0:10]
            selected_kps_fixed = []
            selected_kps_float = []
            for m in selected_matches:
                selected_kps_float.append(kps_float[m.trainIdx].pt)
                selected_kps_fixed.append(kps_fixed[m.queryIdx].pt)
            reprojThresh = 3
            confidence_ratio = 0.86
            (E, status) = cv2.estimateAffinePartial2D(np.float32(selected_kps_fixed), np.float32(selected_kps_float),
                                                      ransacReprojThreshold=reprojThresh, confidence=confidence_ratio)
            if 0 not in status:
                theta = - math.atan2(E[0, 1], E[0, 0]) * 180 / math.pi
                if abs(theta) > 1:
                    reg_status = 0
                    init_reg_offset = (0, 0)
                else:
                    reg_status = 1
                    init_reg_offset = (E[0, 2] * thumbnail_down_rate, E[1, 2] * thumbnail_down_rate)
            else:
                counts = np.count_nonzero(status == 0)
                if counts > 5:  # if over 50% fails
                    reg_status = 0
                    init_reg_offset = (0, 0)
                else:
                    init_reg_offset = (E[0, 2] * thumbnail_down_rate, E[1, 2] * thumbnail_down_rate)
                    reg_status = 1
            return init_reg_offset, reg_status
        except:
            reg_status = 0
            init_reg_offset = (0, 0)
            return init_reg_offset, reg_status


    @staticmethod
    def get_sample_locations(wsi_thumb_mask, init_offset, sample_cnt, thumb_rescale=128, from_fixed_thumb=True):
        pos_indices = np.where(wsi_thumb_mask > 0)
        xy_idx = np.random.choice(pos_indices[0].shape[0], sample_cnt)
        if from_fixed_thumb:
            float_loc_y = np.array((pos_indices[1][xy_idx] * thumb_rescale) + init_offset[0]).astype(np.int)
            float_loc_x = np.array((pos_indices[0][xy_idx] * thumb_rescale) + init_offset[1]).astype(np.int)
        else:
            float_loc_y = np.array((pos_indices[1][xy_idx] * thumb_rescale) - init_offset[0]).astype(np.int)
            float_loc_x = np.array((pos_indices[0][xy_idx] * thumb_rescale) - init_offset[1]).astype(np.int)
        fixed_loc_y = np.array((pos_indices[1][xy_idx] * thumb_rescale)).astype(np.int)
        fixed_loc_x = np.array((pos_indices[0][xy_idx] * thumb_rescale)).astype(np.int)
        return [fixed_loc_x, fixed_loc_y], [float_loc_x, float_loc_y]

    def get_all_sample_indices(self, thumbnail_fixed, init_offset, rescale_rate, patch_counts):
        fixed_foreground_mask = self.tissue_detector.predict(thumbnail_fixed, open_operation=True)
        indices = {}
        for i in range(len(patch_counts)):  # layers
            fixed_indices, float_indices = self.get_sample_locations(fixed_foreground_mask, init_offset, patch_counts[i], thumb_rescale=rescale_rate, from_fixed_thumb=True)
            indices["level_"+str(i+1)] = (fixed_indices, float_indices)
        return indices

    @staticmethod
    def filter_by_content_area(rgb_image_array, area_threshold=0.4, brightness=85):
        rgb_image_array[np.any(rgb_image_array == [0, 0, 0], axis=-1)] = [255, 255, 255]
        lab_img = rgb2lab(rgb_image_array)
        l_img = lab_img[:, :, 0]
        binary_img = l_img < brightness
        tissue_size = np.where(binary_img > 0)[0].size
        tissue_ratio = tissue_size*3/rgb_image_array.size  # 3 channels
        if tissue_ratio > area_threshold:
            return True
        else:
            return False

    def match_sample_patches(self, fixed_wsi_obj, float_wsi_obj, indices_dic, layer_patch_num, layer_patch_size, layer_rescale_factors):
        patches_match_offset_dic = {}
        for l in range(len(layer_patch_size)):
            [fixed_loc_x, fixed_loc_y], [float_loc_x, float_loc_y] = indices_dic.get("level_" + str(l + 1))
            layer_match_offset = []
            layer_matched_patch_cnt = 0
            for p in range(len(fixed_loc_x)):
                fixed_patch = fixed_wsi_obj.read_region((fixed_loc_y[p], fixed_loc_x[p]), l + 1, (layer_patch_size[l], layer_patch_size[l])).convert("RGB")
                float_patch = float_wsi_obj.read_region((float_loc_y[p], float_loc_x[p]), l + 1, (layer_patch_size[l], layer_patch_size[l])).convert("RGB")
                Content_rich_fixed = self.filter_by_content_area(np.array(fixed_patch), area_threshold=0.5)
                Content_rich_float = self.filter_by_content_area(np.array(float_patch), area_threshold=0.5)
                if Content_rich_fixed and Content_rich_float:
                    # p_offset, reg_status = get_initial_pos(fixed_patch, float_patch, layer_rescale_factors[l])
                    p_offset, reg_status = self.fast_reg(fixed_patch, float_patch, layer_rescale_factors[l])
                    if logging.DEBUG == logging.root.level:
                        fig = plt.figure()
                        ax1 = fig.add_subplot(121)
                        ax1.imshow(fixed_patch)
                        ax2 = fig.add_subplot(122)
                        ax2.imshow(float_patch)
                        plt.show()
                    if reg_status > 0:
                        layer_match_offset.append([p_offset[0], p_offset[1]])
                        layer_matched_patch_cnt += 1
                    if layer_matched_patch_cnt == layer_patch_num[l]:
                        break
            logging.debug("Get %d reliable offsets from level %d" % (len(layer_match_offset), l+1))
            patches_match_offset_dic["level_" + str(l + 1)] = layer_match_offset
        return patches_match_offset_dic

    @staticmethod
    def norm(rvalue, newmin, newmax):
        oldmin = min(rvalue)
        oldmax = max(rvalue)
        oldrange = oldmax - oldmin
        newrange = newmax - newmin
        if oldrange == 0:  # Deal with the case where rvalue is constant:
            if oldmin < newmin:  # If rvalue < newmin, set all rvalue values to newmin
                newval = newmin
            elif oldmin > newmax:  # If rvalue > newmax, set all rvalue values to newmax
                newval = newmax
            else:  # If newmin <= rvalue <= newmax, keep rvalue the same
                newval = oldmin
            normal = [newval for _ in rvalue]
        else:
            scale = newrange / oldrange
            normal = [(v - oldmin) * scale + newmin for v in rvalue]
        return normal

    def KDE_all_layers(self, offset_dict, layer_rescale_factors):
        layer_cnt = len(offset_dict.keys())
        offset_kde_score_dit = {}
        for l in range(layer_cnt):
            layer_offsets = np.array(offset_dict["level_" + str(l + 1)])/layer_rescale_factors[l]
            xy = np.vstack([layer_offsets[:, 0], layer_offsets[:, 1]])
            kde_scores = gaussian_kde(xy)(xy)
            norm_kde_scores = self.norm(kde_scores, 0, 1)
            offset_kde_score_dit["level_" + str(l + 1)] = (norm_kde_scores, layer_offsets)
        return offset_kde_score_dit

    @staticmethod
    def HL_fit(offset_kde_score_dit, layer_ratios, layer_weights):
        w_np = []
        x_np = []
        y_np = []
        if not len(offset_kde_score_dit.keys()) == len(layer_weights):
            raise Exception("Not enough values")
        for l in range(len(offset_kde_score_dit.keys())):
            norm_kde_scores, layer_offsets = offset_kde_score_dit["level_" + str(l + 1)]
            x_np = np.concatenate((x_np, layer_offsets[:, 0]))
            y_np = np.concatenate((y_np, layer_offsets[:, 1]))
            w_np = np.concatenate((w_np, np.array(norm_kde_scores)*layer_weights[l]))
        regr_w = linear_model.LinearRegression(fit_intercept=False)
        k_s_w = regr_w.fit(x_np.reshape(-1, 1), y_np.reshape(-1, 1), sample_weight=w_np)
        slop_s_w = k_s_w.coef_[0][0]
        # get final estimation
        _, select_layer_offsets = offset_kde_score_dit["level_" + str(1)]
        xy_offset = np.mean(select_layer_offsets, axis=0)
        x_lv0_k_a = xy_offset[0] * layer_ratios[0]
        est_y_lv0_k_b = x_lv0_k_a * slop_s_w
        y_lv0_k_b = xy_offset[1] * layer_ratios[0]
        est_x_lv0_k_a = y_lv0_k_b / slop_s_w
        k_est_x = round((x_lv0_k_a + est_x_lv0_k_a) / 2)
        k_est_y = round((y_lv0_k_b + est_y_lv0_k_b) / 2)
        refined_offsets = [k_est_x, k_est_y]
        return refined_offsets

    @staticmethod
    def check_all_kde_available(offset_dict, layer_patch_num):
        layer_cnt = len(offset_dict.keys())
        available = True
        for l in range(layer_cnt):
            layer_offsets = np.array(offset_dict["level_" + str(l + 1)])
            if len(layer_offsets) < layer_patch_num[l]:
                available = False
        return available

    # A1. Filter registration results from all layers
    def kde_offset_direct(self, offset_dict, kde_threshold=0.7):
        layer_cnt = len(offset_dict.keys())
        reg_layers = np.empty([0, 2])
        for l in range(layer_cnt):
            layer_offsets = np.array(offset_dict["level_" + str(l + 1)])
            if len(layer_offsets) > 2:
                xy = np.vstack([layer_offsets[:, 0], layer_offsets[:, 1]])
                kde_scores = gaussian_kde(xy)(xy)
                norm_kde_scores = self.norm(kde_scores, 0, 1)
                select_layer_offsets = layer_offsets[np.where(np.array(norm_kde_scores) > kde_threshold)]
                # logging.debug(np.mean(select_layer_offsets, axis=0))
                reg_layers = np.vstack([reg_layers, np.mean(select_layer_offsets, axis=0)])
            elif len(layer_offsets) > 0:
                reg_layers = np.vstack([reg_layers, np.mean(layer_offsets, axis=0)])
        return reg_layers

    def match(self, fixed_wsi_fn, float_wsi_fn):
        rescale_rate = self.rescale_rate
        layer_patch_num = self.layer_patch_num
        layer_patch_max_num = self.layer_patch_max_num
        layer_patch_size = self.layer_patch_size

        fixed_wsi_obj = openslide.open_slide(fixed_wsi_fn)
        float_wsi_obj = openslide.open_slide(float_wsi_fn)

        layer_rescale_factors = fixed_wsi_obj.level_downsamples[1:len(layer_patch_size) + 1]
        thumbnail_fixed, thumbnail_float = self.get_thumbnails(fixed_wsi_obj, float_wsi_obj, rescale_rate)
        #TODO: detect ROI and get larger thumbnail
        init_offset, status = self.get_initial_pos(thumbnail_fixed, thumbnail_float, rescale_rate)

        if status == 0:
            raise Exception("Can't align thumbnail")
        logging.debug("Initial offset: %f, %f" % (init_offset[0], init_offset[1]))

        indices_dict = self.get_all_sample_indices(thumbnail_fixed, init_offset, rescale_rate, layer_patch_max_num)
        offset_dict = self.match_sample_patches(fixed_wsi_obj, float_wsi_obj, indices_dict, layer_patch_num, layer_patch_size, layer_rescale_factors)
        if not bool(offset_dict):  # if empty, means we can just use the thumbnail registration result.
            return init_offset
        if self.check_all_kde_available(offset_dict, layer_patch_num):  # Get enough offsets for KDE and regression
            layer_ratios = fixed_wsi_obj.level_downsamples[0:len(layer_patch_size) + 1]
            offset_kde_score_dit = self.KDE_all_layers(offset_dict, layer_ratios[1:len(layer_patch_size) + 1])
            layer_weights = []
            for la in range(len(layer_ratios)-1):
                layer_weights.append(layer_ratios[la]/layer_ratios[la+1])
            result = self.HL_fit(offset_kde_score_dit, layer_ratios[1:len(layer_patch_size) + 1], layer_weights)
        else:
            reg_layers = self.kde_offset_direct(offset_dict)
            result = np.mean(np.array(reg_layers), axis=0)
        result = (init_offset[0] + result[0], init_offset[1] + result[1])
        return result




class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Re-Stained WSI Registration (Jiang et al.)'
    inQueue = Queue()
    outQueue = Queue()
    updateTimer=0.5
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_OVERLAY
    description = 'Apply Jiang''s method for WSI co-registration'
    pluginType = SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN

    configurationList = list((
                            SlideRunnerPlugin.FilePickerConfigurationEntry(uid='file', name='Second WSI', mask='*.svs;;*.tif'),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid='xoffset', name='X Offset', initValue=0, minValue=-2000, maxValue=2000.0),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid='yoffset', name='Y Offset', initValue=0, minValue=-2000, maxValue=2000.0),
                            SlideRunnerPlugin.PushbuttonPluginConfigurationEntry(uid='match',name='Match')
                            ))


    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        
        pass

    def queueWorker(self):
        oldwsi=None
        quitSignal=False
        sl=None
        detected_offset = None
        sl_main = None
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            image = job.currentImage
            mainWSI = job.slideFilename
            
            if 'file' not in job.configuration:
                continue

            
            if (job.configuration['file'] != oldwsi) and (job.configuration['file']!='') and job.configuration['file']:
                sl = openslide.open_slide(job.configuration['file'])

            if (mainWSI):
                sl_main = openslide.open_slide(mainWSI)

            if (job.trigger is not None) and job.trigger.uid=='match':
                print('Trigger: ',job.trigger)
                self.setProgressBar(0)
                self.setMessage('Calculating optimum offset')
                tissue_detector = TissueDetector("LAB_Threshold", threshold=80) # option 1
                matcher_parameters = MatcherParameters()  # use the default parameters
                matcher = WSI_Matcher(tissue_detector, matcher_parameters)
                detected_offset = matcher.match(mainWSI, job.configuration['file'])
                self.setProgressBar(-1)
                updateConfig = list()
                updateConfig.append(SlideRunnerPlugin.PluginConfigUpdateEntry(SlideRunnerPlugin.PluginConfigurationType.SLIDER_WITH_FLOAT_VALUE, uid='xoffset', value=detected_offset[0]))
                updateConfig.append(SlideRunnerPlugin.PluginConfigUpdateEntry(SlideRunnerPlugin.PluginConfigurationType.SLIDER_WITH_FLOAT_VALUE, uid='yoffset', value=detected_offset[1]))
                self.updateConfiguration(SlideRunnerPlugin.PluginConfigUpdate(updateConfig))                

            if (sl) and (sl_main):
                self.setProgressBar(0)
                print('Reading from: ',job)

                zoomValue=job.coordinates[3]/job.currentImage.shape[0]
                print('Zoom value: ',zoomValue)
                act_level = np.argmin(np.abs(np.asarray(sl.level_downsamples)-zoomValue))
                closest_ds = sl_main.level_downsamples[np.argmin(np.abs(np.asarray(sl_main.level_downsamples)-zoomValue))]

                offset = (job.configuration['xoffset'],job.configuration['yoffset'])
                if (detected_offset is not None):
                    offset=detected_offset

                offset_scaled = [int(x/closest_ds) for x in offset]

                print('Scaled offset is: ',offset_scaled)


                imgarea_w=job.coordinates[2:4]
                size_im = (int(imgarea_w[0]/closest_ds), int(imgarea_w[1]/closest_ds))
                print('Image size: ',size_im)
                location = [int(x+y) for x,y in zip(job.coordinates[0:2],offset)]
                print('Location (original):',job.coordinates[0:2])
                print('Location (offset): ',location)
                img = sl.read_region(location=location, level=act_level, size=size_im)
                img = np.array(img.resize((job.currentImage.shape[1],job.currentImage.shape[0] )))

                self.returnImage(img, job.procId)
                self.setMessage('Align done.')
                self.setProgressBar(-1)


            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue
            print('OTSU plugin: received 1 image from queue')





        