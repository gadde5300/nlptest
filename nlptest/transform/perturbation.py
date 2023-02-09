import random
import re
from abc import ABC, abstractmethod
from functools import reduce
from typing import Dict, List, Optional

import numpy as np

from .utils import (A2B_DICT, CONTRACTION_MAP, DEFAULT_PERTURBATIONS, PERTURB_CLASS_MAP, TYPO_FREQUENCY)
from ..utils.custom_types import Sample, Transformation


class BasePerturbation(ABC):

    @staticmethod
    @abstractmethod
    def transform(sample_list: List[Sample]) -> List[Sample]:
        return NotImplementedError()


class PerturbationFactory:
    """"""

    def __init__(
            self,
            data_handler: List[Sample],
            tests=None
    ) -> None:

        if tests is []:
            tests = DEFAULT_PERTURBATIONS

        self._tests = dict()
        for test in tests:

            if isinstance(test, str):
                if test not in DEFAULT_PERTURBATIONS:
                    raise ValueError(
                        f'Invalid test specification: {test}. Available tests are: {DEFAULT_PERTURBATIONS}')
                self._tests[test] = dict()
            elif isinstance(test, dict):
                test_name = list(test.keys())[0]
                if test_name not in DEFAULT_PERTURBATIONS:
                    raise ValueError(
                        f'Invalid test specification: {test_name}. Available tests are: {DEFAULT_PERTURBATIONS}')
                self._tests[test_name] = reduce(lambda x, y: {**x, **y}, test[test_name])
            else:
                raise ValueError(
                    f'Invalid test configuration! Tests can be '
                    f'[1] test name as string or '
                    f'[2] dictionary of test name and corresponding parameters.'
                )

        # if 'swap_entities' in self._tests:
        #     self._tests['swap_entities']['terminology'] = create_terminology(data_handler)
        #     self._tests['swap_entities']['labels'] = data_handler.label
        #
        # if 'swap_cohyponyms' in self._tests:
        #     self._tests['swap_cohyponyms']['labels'] = data_handler.label

        if "american_to_british" in self._tests:
            self._tests['american_to_british']['accent_map'] = A2B_DICT

        if "british_to_american" in self._tests:
            self._tests['american_to_british']['accent_map'] = {v: k for k, v in A2B_DICT.items()}

        self._data_handler = data_handler

    def transform(self) -> List[Sample]:
        """"""
        # NOTE: I don't know if we need to work with a dataframe of if we can keep it as a List[Sample]
        all_samples = []
        for test_name, params in self._tests.items():
            print(test_name)
            transformed_samples = globals()[PERTURB_CLASS_MAP[test_name]].transform(self._data_handler, **params)
            for sample in transformed_samples:
                sample.test_type = test_name
            all_samples.extend(transformed_samples)
        return all_samples


class UpperCase(BasePerturbation):
    @staticmethod
    def transform(sample_list: List[Sample]) -> List[Sample]:
        """Transform a list of strings with uppercase perturbation
        Args:
            sample_list: List of sentences to apply perturbation.
        Returns:
            List of sentences that uppercase perturbation is applied.
        """
        for sample in sample_list:
            sample.test_case = sample.original.upper()
        return sample_list


class LowerCase(BasePerturbation):
    @staticmethod
    def transform(sample_list: List[Sample]) -> List[Sample]:
        """Transform a list of strings with lowercase perturbation
        Args:
            sample_list: List of sentences to apply perturbation.
        Returns:
            List of sentences that lowercase perturbation is applied.
        """
        for sample in sample_list:
            sample.test_case = sample.original.lower()
        return sample_list


class TitleCase(BasePerturbation):
    @staticmethod
    def transform(sample_list: List[Sample]) -> List[Sample]:
        """Transform a list of strings with titlecase perturbation
        Args:
            sample_list: List of sentences to apply perturbation.
        Returns:
            List of sentences that titlecase perturbation is applied.
        """
        for sample in sample_list:
            sample.test_case = sample.original.title()
        return sample_list


class AddPunctuation(BasePerturbation):
    @staticmethod
    def transform(sample_list: List[Sample], whitelist: Optional[List[str]] = None) -> List[Sample]:
        """Add punctuation at the end of the string, if there is punctuation at the end skip it
        Args:
            sample_list: List of sentences to apply perturbation.
            whitelist: Whitelist for punctuations to add to sentences.
        Returns:
            List of sentences that have punctuation at the end.
        """

        if whitelist is None:
            whitelist = ['!', '?', ',', '.', '-', ':', ';']

        for sample in sample_list:
            if sample.original[-1] not in whitelist:
                sample.test_case = sample.original[:-1] + random.choice(whitelist)
            else:
                sample.test_case = sample.original
        return sample_list


class StripPunctuation(BasePerturbation):
    @staticmethod
    def transform(sample_list: List[Sample], whitelist: Optional[List[str]] = None) -> List[Sample]:
        """Add punctuation from the string, if there isn't punctuation at the end skip it

        Args:
            sample_list: List of sentences to apply perturbation.
            whitelist: Whitelist for punctuations to strip from sentences.
        Returns:
            List of sentences that punctuation is stripped.
        """

        if whitelist is None:
            whitelist = ['!', '?', ',', '.', '-', ':', ';']

        for sample in sample_list:
            if sample.original[-1] in whitelist:
                sample.test_case = sample.original[:-1]
            else:
                sample.test_case = sample.original
        return sample_list


class AddTypo(BasePerturbation):
    @staticmethod
    def transform(sample_list: List[Sample]) -> List[Sample]:
        """Add typo to the sentences using keyboard typo and swap typo.
        Args:
            sample_list: List of sentences to apply perturbation.
        Returns:
            List of sentences that typo introduced.
        """
        for sample in sample_list:
            if len(sample.original) < 5:
                sample.test_case = sample.original
                continue

            string = list(sample.original)
            if random.random() > 0.1:
                idx_list = list(range(len(TYPO_FREQUENCY)))
                char_list = list(TYPO_FREQUENCY.keys())

                counter, idx = 0, -1
                while counter < 10 and idx == -1:
                    idx = random.randint(0, len(string) - 1)
                    char = string[idx]
                    if TYPO_FREQUENCY.get(char.lower(), None):
                        char_frequency = TYPO_FREQUENCY[char.lower()]

                        if sum(char_frequency) > 0:
                            chosen_char = random.choices(idx_list, weights=char_frequency)
                            difference = ord(char.lower()) - ord(char_list[chosen_char[0]])
                            char = chr(ord(char) - difference)
                            string[idx] = char
                    else:
                        idx = -1
                        counter += 1
            else:
                string = list(string)
                swap_idx = random.randint(0, len(string) - 2)
                tmp = string[swap_idx]
                string[swap_idx] = string[swap_idx + 1]
                string[swap_idx + 1] = tmp

            sample.test_case = "".join(string)
        return sample_list


class SwapEntities(BasePerturbation):
    @staticmethod
    def transform(
            sample_list: List[Sample],
            labels: List[List[str]] = None,
            terminology: Dict[str, List[str]] = None
    ) -> List[Sample]:
        """Swaps named entities with the new one from the terminology extracted from passed data.

        Args:
            sample_list: List of sentences to process.
            labels: Corresponding labels to make changes according to sentences.
            terminology: Dictionary of entities and corresponding list of words.
        Returns:
            List of sentences that entities swapped with the terminology.
        """

        if terminology is None:
            raise ValueError('In order to generate test cases for swap_entities, terminology should be passed!')

        if labels is None:
            raise ValueError('In order to generate test cases for swap_entities, labels should be passed!')

        for idx, sample in enumerate(sample_list):
            sent_tokens = sample.original.split(' ')
            sent_labels = labels[idx]

            ent_start_pos = np.array([1 if label[0] == 'B' else 0 for label in sent_labels])
            ent_idx, = np.where(ent_start_pos == 1)

            #  no swaps since there is no entity in the sentence
            if len(ent_idx) == 0:
                sample.test_case = sample.original
                continue

            replace_idx = np.random.choice(ent_idx)
            ent_type = sent_labels[replace_idx][2:]
            replace_idxs = [replace_idx]
            if replace_idx < len(sent_labels) - 1:
                for i, label in enumerate(sent_labels[replace_idx + 1:]):
                    if label == f'I-{ent_type}':
                        replace_idxs.append(i + replace_idx + 1)
                    else:
                        break

            replace_token = sent_tokens[replace_idx: replace_idx + len(replace_idxs)]
            token_length = len(replace_token)
            replace_token = " ".join(replace_token)

            proper_entities = [ent for ent in terminology[ent_type] if len(ent.split(' ')) == token_length]
            chosen_ent = random.choice(proper_entities)
            replaced_string = sample.original.replace(replace_token, chosen_ent)
            sample.test_case = replaced_string
        return sample_list


def get_cohyponyms_wordnet(word: str) -> str:
    """
    Retrieve co-hyponym of the input string using WordNet when a hit is found.

    Args:
        word: input string to retrieve co-hyponym
    Returns:
        Cohyponym of the input word if exists, else original word.
    """

    try:
        import wn
    except ImportError:
        raise ImportError("WordNet is not available!\n"
                          "Please install WordNet via pip install wordnet to use swap_cohyponyms")

    orig_word = word
    word = word.lower()
    if len(word.split()) > 0:
        word = word.replace(" ", "_")
    syns = wn.synsets(word)

    if len(syns) == 0:
        return orig_word
    else:
        hypernym = syns[0].hypernyms()
        if len(hypernym) == 0:
            return orig_word
        else:
            hypos = hypernym[0].hyponyms()
            hypo_len = len(hypos)
            if hypo_len == 1:
                name = hypos[0].lemmas()[0]
            else:
                ind = random.sample(range(hypo_len), k=1)[0]
                name = hypos[ind].lemmas()[0]
                while name == word:
                    ind = random.sample(range(hypo_len), k=1)[0]
                    name = hypos[ind].lemmas()[0]
            return name.replace("_", " ")


class SwapCohyponyms(BasePerturbation):

    @staticmethod
    def transform(
            sample_list: List[Sample],
            labels: List[List[str]] = None,
    ) -> List[Sample]:
        """Swaps named entities with the new one from the terminology extracted from passed data.

        Args:
            sample_list: List of sentences to process.
            labels: Corresponding labels to make changes according to sentences.

        Returns:
            List sample indexes and corresponding augmented sentences, tags and labels if provided.
        """

        if labels is None:
            raise ValueError('In order to generate test cases for swap_entities, terminology should be passed!')

        perturb_sent = []
        for idx, sample in enumerate(sample_list):
            sent_tokens = sample.original.split(' ')
            sent_labels = labels[idx]

            ent_start_pos = np.array([1 if label[0] == 'B' else 0 for label in sent_labels])
            ent_idx, = np.where(ent_start_pos == 1)

            #  no swaps since there is no entity in the sentence
            if len(ent_idx) == 0:
                sample.test_case = sample.original
                continue

            replace_idx = np.random.choice(ent_idx)
            ent_type = sent_labels[replace_idx][2:]
            replace_idxs = [replace_idx]
            if replace_idx < len(sent_labels) - 1:
                for i, label in enumerate(sent_labels[replace_idx + 1:]):
                    if label == f'I-{ent_type}':
                        replace_idxs.append(i + replace_idx + 1)
                    else:
                        break

            replace_token = sent_tokens[replace_idx: replace_idx + len(replace_idxs)]

            replace_token = " ".join(replace_token)
            chosen_ent = get_cohyponyms_wordnet(replace_token)
            replaced_string = sample.original.replace(replace_token, chosen_ent)
            perturb_sent.append(replaced_string)

        return sample_list


class ConvertAccent(BasePerturbation):

    @staticmethod
    def transform(sample_list: List[Sample], accent_map: Dict[str, str] = None) -> List[Sample]:
        """Converts input sentences using a conversion dictionary
        Args:
            sample_list: List of sentences to process.
            accent_map: Dictionary with conversion terms.
        Returns:
            List of sentences that perturbed with accent conversion.
        """
        perturb_sent = []
        for sample in sample_list:
            tokens = sample.original.split(' ')
            tokens = [accent_map[t.lower()] if accent_map.get(t.lower(), None) else t for t in tokens]
            sample.test_case = ' '.join(tokens)

        return perturb_sent


class AddContext(BasePerturbation):

    @staticmethod
    def transform(
            sample_list: List[Sample],
            starting_context: Optional[List[str]] = None,
            ending_context: Optional[List[str]] = None,
            strategy: List[str] = None,
    ) -> List[Sample]:
        """Converts input sentences using a conversion dictionary
        Args:
            sample_list: List of sentences to process.
            strategy: Config method to adjust where will context tokens added. start, end or combined.
            starting_context: list of terms (context) to input at start of sentences.
            ending_context: list of terms (context) to input at end of sentences.
        Returns:
            List of sentences that context added at to begging, end or both, randomly.
        """

        possible_methods = ['start', 'end', 'combined']
        for sample in sample_list:
            if strategy is None:
                strategy = random.choice(possible_methods)
            elif strategy not in possible_methods:
                raise ValueError(
                    f"Add context strategy must be one of 'start', 'end', 'combined'. Cannot be {strategy}."
                )

            transformations = []
            if strategy == "start" or strategy == "combined":
                add_tokens = random.choice(starting_context)
                add_string = " ".join(add_tokens) if isinstance(add_tokens, list) else add_tokens
                string = add_string + ' ' + sample.original
                transformations.append(
                    Transformation(from_start_char=0, to_start_char=0, from_end_char=0, to_end_char=len(add_string) + 1,
                                   ignore=True)
                )
            else:
                string = sample.original

            if strategy == "end" or strategy == "combined":
                add_tokens = random.choice(ending_context)
                add_string = " ".join(add_tokens) if isinstance(add_tokens, list) else add_tokens

                if sample.original[-1].isalnum():
                    from_start, from_end = len(string), len(string)
                    to_start = from_start + 1
                    to_end = to_start + len(add_string)
                    string = string + ' ' + add_string
                else:
                    from_start, from_end = len(string[:-1]), len(string[:-1])
                    to_start = from_start
                    to_end = to_start + len(add_string)
                    string = string[:-1] + add_string + " " + string[-1]

                transformations.append(
                    Transformation(from_start_char=from_start, to_start_char=to_start, from_end_char=from_end,
                                   to_end_char=to_end, ignore=True)
                )

            sample.test_case = string
            sample.transformations = transformations
        return sample_list


class AddContraction(BasePerturbation):

    @staticmethod
    def transform(
            sample_list: List[Sample],
    ) -> List[str]:
        """Converts input sentences using a conversion dictionary
        Args:
            sample_list: List of sentences to process.
        """

        def custom_replace(match):
            """
              regex replace for contraction.
            """
            token = match.group(0)
            contracted_token = CONTRACTION_MAP.get(token, CONTRACTION_MAP.get(token.lower()))

            is_upper_case = token[0]
            expanded_contraction = is_upper_case + contracted_token[1:]
            return expanded_contraction

        perturb_sent = []
        for sample in sample_list:
            string = sample.original
            for contraction in CONTRACTION_MAP:
                if re.search(contraction, sample.original, flags=re.IGNORECASE | re.DOTALL):
                    string = re.sub(contraction, custom_replace, sample.original, flags=re.IGNORECASE | re.DOTALL)
            sample.test_case = string
        return perturb_sent
