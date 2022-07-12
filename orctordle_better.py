import os
import itertools
import random
import pickle
from tqdm import tqdm
from scipy.stats import entropy
from collections import defaultdict, Counter
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By

N_GUESSES = 13
N_GRIDS = 8
DICT_FILE_all = 'words.txt'

driver = webdriver.Firefox()
driver.get("https://octordle.com/free")


with open(DICT_FILE_all) as ifp:
    all_dictionary = list(map(lambda x: x.strip(), ifp.readlines()))

error_msg = 'Dictionary contains different length words.'
assert len({len(x) for x in all_dictionary}) == 1, error_msg
print(f'Loaded dictionary with {len(all_dictionary)} words...')
WORD_LEN = len(all_dictionary[0])
all_patterns = list(itertools.product([0, 1, 2], repeat=WORD_LEN))


if 'pattern_dict.p' in os.listdir('.'):
    pattern_dict_unit = pickle.load(open('pattern_dict.p', 'rb'))
else:
    pattern_dict_unit = generate_pattern_dict(all_dictionary)
    pickle.dump(pattern_dict_unit, open('pattern_dict.p', 'wb+'))

input("When the page is ready, press Enter to continue...")

keys = driver.find_elements(By.CLASS_NAME, "keyboard-letter")
enter = driver.find_element(By.CLASS_NAME, "keyboard-letter.control-char.enter")

def get_patterns(round):
    boards = driver.find_elements(By.CLASS_NAME, "board")
    patterns = []
    for board in boards:
        rows = board.find_elements(By.CLASS_NAME, "board-row")
        row = rows[round]
        letters = row.find_elements(By.XPATH, './/div')
        pattern = []
        for letter in letters:
            if letter.get_attribute("class") != 'letter-content':
                if letter.get_attribute("class") == 'letter guessed past-guess':
                    pattern.append(0)
                elif letter.get_attribute("class") == 'letter word-match guessed past-guess':
                    pattern.append(1)
                elif letter.get_attribute("class") == 'letter exact-match guessed past-guess':
                    pattern.append(2)
                else:
                    print("smth wrong")
        patterns.append(tuple(pattern))
    return patterns

def type_word(word):
    for letter in word:
        for key in keys:
            if key.find_element(By.XPATH, ".//div").text == letter.upper():
                key.click()
    enter.click()

def generate_pattern_dict(dictionary):

    pattern_dict = defaultdict(lambda: defaultdict(set))
    for word in tqdm(dictionary):
        for word2 in dictionary:
            pattern = calculate_pattern(word, word2)
            pattern_dict[word][pattern].add(word2)
    return dict(pattern_dict)


def calculate_entropies(words, possible_words, pattern_dict, all_patterns):
    entropies = {}
    for word in words:
        counts = []
        for pattern in all_patterns:
            matches = pattern_dict[word][pattern]
            matches = matches.intersection(possible_words)
            counts.append(len(matches))
        entropies[word] = entropy(counts)
    return entropies

print("Starting game")
check = True

while check:
    grids = set([i for i in range(N_GRIDS)])
    candidates = ['' for i in range(N_GRIDS)]
    entropies = ['' for i in range(N_GRIDS)]
    pattern_dict = [pattern_dict_unit for i in range(N_GRIDS)]
    infos = ['' for i in range(N_GRIDS)]
    words = ['' for i in range(N_GRIDS)]
    results = ['' for i in range(N_GRIDS)]

    all_words = [set(all_dictionary) for x in grids]
    init_round = 0

    for n_round in range(N_GUESSES):
        for i in grids:
            candidates[i] = all_words[i]
            entropies[i] = calculate_entropies(candidates[i], all_words[i], pattern_dict[i], all_patterns)

        total_entropies = {}
        for i in grids:
            total_entropies = {k: total_entropies.get(k, 0) + entropies[i].get(k, 0) for k in set(total_entropies) | set(entropies[i])}

        guess_word = max(total_entropies.items(), key=lambda x: x[1])[0]

        type_word(guess_word)

        resulting_patterns = get_patterns(n_round)
        while resulting_patterns == [(), (), (), (), (), (), (), ()]:
            resulting_patterns = get_patterns(n_round)
            sleep(1)
            print("Trying to fetch info again... Check your connexion")
        for i in grids:
            infos[i] = resulting_patterns[i]

        print('Guessing:     ', guess_word)
        print('Info:         ', infos)
        toremove = []
        for i in grids:
            if infos[i] == (2, 2, 2, 2, 2):
                results[i] = guess_word
                toremove.append(i)
        for x in toremove:
            grids.remove(x)
        print('Remaining grids:', grids)
        if len(grids) == 0:
            print(f'WIN IN {n_round + 1} GUESSES!\n\n\n')
            break

        for i in grids:
            words[i] = pattern_dict[i][guess_word][infos[i]]
            all_words[i] = all_words[i].intersection(words[i])
    if n_round == N_GUESSES - 1:
        print("Such a hard game, we failed :(")

    sleep(1)
    inf_loop = True
    while inf_loop:
        a = input("Start a new game and press [y] to try again, or [q] to quit\n")
        if a == 'q':
            check = False
            inf_loop = False
        elif a == 'y':
            inf_loop = False

driver.close()