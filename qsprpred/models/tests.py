import os
import shutil
from os.path import exists
from unittest import TestCase
import random

import pandas as pd
import torch
from QSPRpred.qsprpred.data.utils.descriptorcalculator import descriptorsCalculator
from QSPRpred.qsprpred.data.utils.descriptors import MorganFP
from qsprpred.data.data import QSPRDataset
from qsprpred.logs import logger
from qsprpred.models.models import QSPRDNN, QSPRsklearn
from qsprpred.models.neural_network import STFullyConnected
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC, SVR
from torch.utils.data import DataLoader, TensorDataset
from xgboost import XGBClassifier, XGBRegressor


class PathMixIn:
    datapath = f'{os.path.dirname(__file__)}/test_files/data'
    envspath = f'{os.path.dirname(__file__)}/test_files/envs'

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls.envspath):
            os.mkdir(cls.envspath)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.envspath)

class NeuralNet(PathMixIn, TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        os.remove(f'{cls.datapath}/testmodel.log')
        os.remove(f'{cls.datapath}/testmodel.pkg')

    def prep_testdata(self, reg=True, th=[]):
        reg_abbr = 'REG' if reg else 'CLS'
        
        # prepare test dataset
        df = pd.read_csv(f'{self.datapath}/test_data_large.tsv', sep='\t')
        data = QSPRDataset(df=df, property="CL", reg=reg, th=th)
        data.prepareDataset(f'{os.path.dirname(__file__)}/test_files/envs/CL_{reg_abbr}.tsv',
                                feature_calculators=descriptorsCalculator([MorganFP(3, 1000)]))
        data.X, data.X_ind = data.dataStandardization(data.X, data.X_ind)

        # prepare data for torch DNN
        y = data.y.reshape(-1,1)
        y_ind = data.y_ind.reshape(-1,1)

        trainloader = DataLoader(TensorDataset(torch.Tensor(data.X), torch.Tensor(y)), batch_size=100)
        testloader = DataLoader(TensorDataset(torch.Tensor(data.X_ind), torch.Tensor(y_ind)), batch_size=100)

        return data.X.shape[1], trainloader, testloader

    def test_STFullyConnected(self):
        ## prepare test regression dataset
        no_features, trainloader, testloader = self.prep_testdata(reg=True)

        # fit model with default settings
        model = STFullyConnected(n_dim = no_features)
        model.fit(trainloader, testloader, out=f'{self.datapath}/testmodel', patience = 3)

        # fit model with non-default epochs and learning rate and tolerance
        model = STFullyConnected(n_dim = no_features, n_epochs = 50, lr = 0.5)
        model.fit(trainloader, testloader, out=f'{self.datapath}/testmodel', patience = 3, tol=0.01)

        # fit model with non-default settings for model construction
        model = STFullyConnected(n_dim = no_features, neurons_h1=2000, neurons_hx=500, extra_layer=True)
        model.fit(trainloader, testloader, out=f'{self.datapath}/testmodel', patience = 3)

        ## prepare classification test dataset
        no_features, trainloader, testloader = self.prep_testdata(reg=False, th=[6.5])

        # fit model with regression is false
        model = STFullyConnected(n_dim = no_features, is_reg=False)
        model.fit(trainloader, testloader, out=f'{self.datapath}/testmodel', patience = 3)

        ## prepare multi-classification test dataset
        no_features, trainloader, testloader = self.prep_testdata(reg=False, th=[0, 1, 10, 1200])

        # fit model with regression is false
        model = STFullyConnected(n_dim = no_features, n_class=3, is_reg=False)
        model.fit(trainloader, testloader, out=f'{self.datapath}/testmodel', patience = 3)


class TestModels(PathMixIn, TestCase):

    def prep_testdata(self, reg=True, th=[]):
        
        reg_abbr = 'REG' if reg else 'CLS'
        random.seed(42)

        # prepare test dataset
        df = pd.read_csv(f'{self.datapath}/test_data_large.tsv', sep='\t')
        data = QSPRDataset(df=df, property="CL", reg=reg, th=th)
        data.prepareDataset(f'{os.path.dirname(__file__)}/test_files/envs/CL_{reg_abbr}.tsv',
                                feature_calculators=descriptorsCalculator([MorganFP(3, 1000)]))
        data.X, data.X_ind = data.dataStandardization(data.X, data.X_ind)
        
        return data

    def QSPRsklearn_models_test(self, alg, alg_name, reg, th=[], n_jobs=8):
        #intialize dataset and model
        data = self.prep_testdata(reg=reg, th=th)
        themodel = QSPRsklearn(base_dir = f'{os.path.dirname(__file__)}/test_files/',
                               data=data, alg = alg, alg_name=alg_name, n_jobs=n_jobs)
        
        # train the model on all data
        themodel.fit()
        regid = 'REG' if reg else 'CLS'
        self.assertTrue(exists(f'{os.path.dirname(__file__)}/test_files/envs/{alg_name}_{regid}_{data.property}.pkg'))

        # perform crossvalidation
        themodel.evaluate()
        self.assertTrue(exists(f'{os.path.dirname(__file__)}/test_files/envs/{alg_name}_{regid}_{data.property}.ind.tsv'))
        self.assertTrue(exists(f'{os.path.dirname(__file__)}/test_files/envs/{alg_name}_{regid}_{data.property}.cv.tsv'))
        
        # perform bayes optimization
        fname = f'{os.path.dirname(__file__)}/test_files/search_space_test.json'
        grid_params = QSPRsklearn.loadParamsGrid(fname, "bayes", alg_name)
        search_space_bs = grid_params[grid_params[:,0] == alg_name,1][0]
        themodel.bayesOptimization(search_space_bs=search_space_bs, n_trials=1)
        self.assertTrue(exists(f'{os.path.dirname(__file__)}/test_files/envs/{alg_name}_{regid}_{data.property}_params.json'))

        # perform grid search
        os.remove(f'{os.path.dirname(__file__)}/test_files/envs/{alg_name}_{regid}_{data.property}_params.json')
        grid_params = QSPRsklearn.loadParamsGrid(fname, "grid", alg_name)
        search_space_gs = grid_params[grid_params[:,0] == alg_name,1][0]
        themodel.gridSearch(search_space_gs=search_space_gs)
        self.assertTrue(exists(f'{os.path.dirname(__file__)}/test_files/envs/{alg_name}_{regid}_{data.property}_params.json'))


    def testRF(self):
        alg_name = "RF"
        #test regression
        alg = RandomForestRegressor()
        self.QSPRsklearn_models_test(alg, alg_name, reg=True)

        #test classifier
        alg = RandomForestClassifier()
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[6.5])
        
        #test multi-classifier
        alg = RandomForestClassifier()
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[0, 1, 10, 1100])

    def testKNN(self):
        alg_name = "KNN"
        # test regression
        alg = KNeighborsRegressor()
        self.QSPRsklearn_models_test(alg, alg_name, reg=True)

        # test classifier
        alg = KNeighborsClassifier()
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[6.5])

        # test multiclass
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[0, 1, 10, 1100])

    def testXGB(self):
        alg_name = "XGB"
        #test regression
        alg = XGBRegressor(objective='reg:squarederror')
        self.QSPRsklearn_models_test(alg, alg_name, reg=True)

        #test classifier
        alg = XGBClassifier(objective='binary:logistic', use_label_encoder=False, eval_metric='logloss')
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[6.5])

        #test multiclass
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[0, 1, 10, 1100])

    def testSVM(self):
        alg_name = "SVM"
        #test regression
        alg = SVR()
        self.QSPRsklearn_models_test(alg, alg_name, reg=True)

        #test classifier
        alg = SVC(probability=True)
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[6.5])

        #test multiclass
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[0, 1, 10, 1100])

    def testPLS(self):
        alg_name = "PLS"
        #test regression
        alg = PLSRegression()
        self.QSPRsklearn_models_test(alg, alg_name, reg=True)

    def testNB(self):
        alg_name = "NB"
        #test classfier
        alg = GaussianNB()
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[6.5])

        #test multiclass
        self.QSPRsklearn_models_test(alg, alg_name, reg=False, th=[0, 1, 10, 1100])

    def test_QSPRDNN(self):
        #intialize model for single class, multi class and regression DNN's
        for reg in [(False, [0, 1, 10, 1100]), (False, [6.5]), (True, [])]:
            data = self.prep_testdata(reg=reg[0], th=reg[1])
            themodel = QSPRDNN(base_dir = f'{os.path.dirname(__file__)}/test_files/', data=data, gpus=[3,2], patience=3, tol=0.02)
            
            #fit and cross-validation
            themodel.evaluate()
            themodel.fit()

            #optimization
            fname = f'{os.path.dirname(__file__)}/test_files/search_space_test.json'

            # grid search
            grid_params = QSPRDNN.loadParamsGrid(fname, "grid", "DNN")
            search_space_gs = grid_params[grid_params[:,0] == "DNN",1][0]
            themodel.gridSearch(search_space_gs=search_space_gs)
  
            # bayesian optimization
            bayes_params = QSPRDNN.loadParamsGrid(fname, "bayes", "DNN")
            search_space_bs = bayes_params[bayes_params[:,0] == "DNN",1][0]
            themodel.bayesOptimization(search_space_bs=search_space_bs, n_trials=5)