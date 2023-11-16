import os
import cv2
import math
import time
import numpy as np
from PIL import Image
from datetime import datetime
from matplotlib import pyplot as plt

from model.resnet import get_resnet
from utils.utils_log import LogFactory


log = LogFactory.get_log('audit')


class CallResNet:
    def __init__(self, img_input):
        self.img_input = img_input # img:input path like as "/tmp/XXX.png"
        self.output_path = "/outputs"
        self.model = get_resnet()
        self.model.load_weights('./model/d_A_epoch100.h5', skip_mismatch=True, by_name=True)
        self.encrypted_figure = np.zeros((256, 256, 3), dtype=np.int32)

    def reshape_fig(self):
        # check the cv2.imread() function
        log.info("[reshape_fig] start to reshape the input image")
        img = cv2.imread(self.img_input)
        cvt_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        log.info("[reshape_fig] convert the input image from BGR to RGB")
        resized_img = cv2.resize(cvt_img, (256, 256))
        log.info("[reshape_fig] resize the input image to 256*256")
        narray_img = np.array(resized_img)
        reshaped_img = narray_img.reshape(256, 256, 3)
        log.info("[reshape_fig] reshape the input image to 256*256*3")
        return reshaped_img

    @staticmethod
    def initialized_seed():
        # call the random seed generator in the api
        log.info("[initialized_seed] start to generate the random seed")
        raw_seed = np.random.randint(0, 20000001, size=(1, 256, 256, 3))
        random_seed = np.array(raw_seed, dtype=np.float32) / 10000000 - 1
        log.info("[initialized_seed] generate the random seed successfully")
        return random_seed

    def generate_random_image(self, input_seed):
        log.info("[generate_random_image] start to generate the random image")
        latent_fake = self.model.predict(input_seed)
        log.info("[generate_random_image] generate the random image successfully")
        formulated_latent_fake = np.int32(latent_fake)
        log.info("[generate_random_image] formulate the random image successfully")
        return formulated_latent_fake

    def encrypt_fig(self, seed):
        log.info("[encrypt_fig] start to encrypt the input image")
        start_time = time.time()
        raw_fig = self.reshape_fig()
        random_img = self.generate_random_image(seed)
        for a in range(256):
            for b in range(256):
                for c in range(3):
                    self.encrypted_figure[a, b, c] = random_img[0, a, b, c] ^ raw_fig[a, b, c]
        end_time = time.time()
        encrypt_period = end_time - start_time
        log.info("[encrypt_fig] the period of encryption is {}s".format(encrypt_period))
        encrypted_fig = Image.fromarray(np.uint8(self.encrypted_figure))
        encrypted_fig_path = os.path.join(self.output_path,
                                          "encrypted_fig_{}.png".format(datetime.now().strftime("%Y%m%d%H%M%S")))
        encrypted_fig.save(encrypted_fig_path)
        log.info("[encrypt_fig] save the encrypted image to {}".format(encrypted_fig_path))
        return encrypt_period, encrypted_fig_path

    def cal_entropy(self):
        log.info("[cal_entropy] start to calculate the entropy of encrypted image")
        e = 0
        pp = np.zeros(256, dtype=np.float32)
        for a in range(256):
            for b in range(256):
                for c in range(3):
                    g = self.encrypted_figure[a, b, c]
                    pp[int(g)] = pp[int(g)] + 1
        for z2 in range(256):
            if pp[z2] != 0:
                e += -(pp[z2] / (256 * 256 * 3)) * (math.log(pp[z2] / (256 * 256 * 3)) / math.log(2.0))
        log.info("[cal_entropy] the entropy of encrypted image is {}".format(e))
        return e, pp

    def decrypt_fig(self, seed):
        log.info("[decrypt_fig] start to decrypt the encrypted image")
        start_time = time.time()
        random_img = self.generate_random_image(seed)
        for a in range(256):
            for b in range(256):
                for c in range(3):
                    self.encrypted_figure[a, b, c] = random_img[0, a, b, c] ^ self.encrypted_figure[a, b, c]
        end_time = time.time()
        decrypt_period = end_time - start_time
        log.info("[decrypt_fig] the period of decryption is {}s".format(decrypt_period))
        return decrypt_period

    def estimate_performance(self, encrypt_period, decrypt_period, entropy_value, entropy_pp):
        log.info("[estimate_performance] start to estimate the performance of encryption and decryption")
        plt.figure()
        plt.annotate('encryption_time: {}, \ndecryption_time: {}, \ninformation_entropy: {}'.format(
            encrypt_period, decrypt_period, entropy_value), xy=(0, 0), xytext=(0, 1.2),
                     textcoords="axes fraction", fontsize=12,
                     xycoords="axes fraction", ha="left", va="bottom")
        log.info("[estimate_performance] adding the annotation: {}, {}, {}".format(encrypt_period,
                                                                                   decrypt_period, entropy_value))
        plt.title("Grayscale Histogram of Ciphertext Image")
        plt.xlabel("Pixel Value")
        plt.ylabel("Numbers of Pixels")
        plt.bar(range(256), entropy_pp, width=1)
        plt.xlim([0, 255])
        plt.ylim([0, 1600])
        performance_fig_path = os.path.join(self.output_path,
                                            "performance_fig_{}.png".format(datetime.now().strftime("%Y%m%d%H%M%S")))
        plt.savefig(performance_fig_path, bbox_inches='tight', pad_inches=0)
        log.info("[estimate_performance] save the performance figure to {}".format(performance_fig_path))
        return performance_fig_path
