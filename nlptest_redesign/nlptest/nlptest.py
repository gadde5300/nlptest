from functools import reduce
from typing import Optional, Union

import pandas as pd
import numpy as np
import yaml

from .datahandler.datasource import DataFactory
from .modelhandler import ModelFactory
from .testrunner import TestRunner
from .transform.pertubation import PertubationFactory

class Harness:
    """ Harness is a testing class for NLP models.

    Harness class evaluates the performance of a given NLP model. Given test data is
    used to test the model. A report is generated with test results.
    """

    def __init__(
            self,
            task: Optional[str],
            model: Union[str, ModelFactory],
            data: Optional[str] = None,
            config: Optional[Union[str, dict]] = None
    ):
        """
        Initialize the Harness object.

        Args:
            task (str, optional): Task for which the model is to be evaluated.
            model (str | ModelFactory): ModelFactory object or path to the model to be evaluated.
            data (str, optional): Path to the data to be used for evaluation.
            config (str | dict, optional): Configuration for the tests to be performed.
        """

        super().__init__()
        self.task = task

        if isinstance(model, ModelFactory):
            assert model.task == task, \
                "The 'task' passed as argument as the 'task' with which the model has been initialized are different."
            self.model = model
        elif isinstance(model, str):
            self.model = ModelFactory(task=task, model_path=model)

        else:
          self.model=model
          if "sparknlp.pretrained" in str(type(self.model)):
            self.model.backend="sparknlp.pretrained"
          else:
            self.model.backend="spark"

        if data is not None:
            # self.data = data
            if type(data) == str:
                self.data = DataFactory(data).load()
            # else:
            #     self.data = DataFactory.load_hf(data)
        if config is not None:
            self._config = self.configure(config)

    def configure(self, config):
        """
        Configure the Harness with a given configuration.

        Args:
            config (str | dict): Configuration file path or dictionary
                for the tests to be performed.

        Returns:
            dict: Loaded configuration.
        """

        if type(config) == dict:
            self._config = config
        else:
            with open(config, 'r') as yml:
                self._config = yaml.safe_load(yml)

        return self._config

    def generate(self) -> None:
        """
        Generates the testcases to be used when evaluating the model.

        Returns:
            None: The generated testcases are stored in `_load_testcases` attribute.
        """

        # self.data_handler =  DataFactory(data_path).load()
        # self.data_handler = self.data_handler(file_path = data_path)
        tests = self._config['tests_types']
        if len(tests) != 0:
            self._load_testcases = PertubationFactory(self.data, tests).transform()
        else:
            self._load_testcases = PertubationFactory(self.data).transform()
        return self

    # def load(self) -> pd.DataFrame:
    #     try:
    #         self._load_testcases = pd.read_csv('path/to/{self._model_path}_testcases')
    #         if self.load_testcases.empty:
    #             self.load_testcases = self.generate()
    #         # We have to make sure that loaded testcases df are editable in Qgrid
    #         return self.load_testcases
    #     except:
    #         self.generate()

    def run(self) -> None:
        """
        Run the tests on the model using the generated testcases.

        Returns:
            None: The evaluations are stored in `_generated_results` attribute.
        """
        self._generated_results = TestRunner(self._load_testcases, self.model).evaluate()
        return self

    def report(self) -> pd.DataFrame:
        """
        Generate a report of the test results.

        Returns:
            pd.DataFrame: DataFrame containing the results of the tests.
        """
         # summary = pd.pivot_table()
        if isinstance(self._config['min_pass_rate'], list):
            min_pass_dict = reduce(lambda x, y: {**x, **y}, self._config['min_pass_rate'])
        else:
            min_pass_dict = self._config['min_pass_rate']

        temp_df = pd.concat(
            [self._generated_results, pd.get_dummies(self._generated_results['is_pass'], prefix='bool')],
            axis=1
        )
        summary = temp_df.pivot_table(
            values=['bool_True', 'bool_False'],
            index=['Test_type'],
            aggfunc=np.sum
        ).reset_index()
        
        summary['minimum_pass_rate'] = \
            summary.apply(
                lambda x: min_pass_dict[x['Test_type']] \
                if x['Test_type'] in list(min_pass_dict.keys())\
                else min_pass_dict['default'], 
                axis=1)
        summary['pass_rate'] = summary['bool_True']/(summary['bool_True'] + summary['bool_False'])
        summary['pass'] = summary['minimum_pass_rate'] < summary['pass_rate']
        summary.columns = ['Test_type', 'fail_count', 'pass_count',	'minimum_pass_rate', 'pass_rate', 'pass']

        return summary

    def save(self, config: str = "test_config.yml", testcases: str = "test_cases.csv",
             results: str = "test_results.csv"):
        """
        Save the configuration, generated testcases, and results
        of the evaluations as yml and csv files.

        Parameters:
            config (str, optional): Path to the YAML file for the configuration.
                Default is "test_config.yml".
            testcases (str, optional): Path to the CSV file for the generated testcases.
                Default is "test_cases.csv".
            results (str, optional): Path to the CSV file for the results of the evaluations.
                Default is "test_results.csv".

        Returns:
            None
        """

        with open(config, 'w') as yml:
            yml.write(yaml.safe_dump(self._config))

        self._load_testcases.to_csv(testcases, index=None)
        self._generated_results.to_csv(results, index=None)