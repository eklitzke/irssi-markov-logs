import optparse
import random
import re
import string
import time


ALLOWED_CHARS = frozenset(string.letters)


class Sigil(object):
    pass


class StartSentence(Sigil):
    pass


class EndSentence(Sigil):
    pass


class Counter(object):

    def __init__(self):
        self.counts = {}

    def add(self, key):
        self.counts.setdefault(key, 0)
        self.counts[key] += 1

    def to_probability_array(self):
        probability_array = []
        total = float(sum(self.counts.itervalues()))
        running_total = 0
        for k, v in self.counts.iteritems():
            running_total += v / total
            probability_array.append((k, running_total))
        return probability_array



class Word(object):

    def __init__(self):
        self.variations = Counter()
        self.next_words = Counter()
        self.probvar = None
        self.probnext = None
        self.is_start = False
        self.is_end = False

    def add(self, form):
        if isinstance(form, basestring):
            # strip trailing end-of-sentence punctuation
            form = form.rstrip('!?.')
        elif type(form) is StartSentence:
            self.is_start = True
        elif type(form) is EndSentence:
            self.is_end = True
        self.variations.add(form)

    def add_next(self, word):
        self.next_words.add(word)

    def construct_probabilities(self):
        self.probvar = self.variations.to_probability_array()
        self.probnext = self.next_words.to_probability_array()

    @staticmethod
    def normalize_word(word):
        if isinstance(word, basestring):
            return ''.join(c for c in word if c in ALLOWED_CHARS)
        else:
            return word


def get_pairs(iterable, start, end):
    listform = list(iterable)
    if not listform:
        return
    yield start, listform[0]
    for i in xrange(len(listform) - 1):
        yield listform[i], listform[i + 1]
    yield listform[-1], end


def pick(array):
    r = random.random()
    for item, total in array:
        if total >= r:
            return item
    return item


def build_adjacencies(nick1, nick2, logfile):
    words1, words2 = {}, {}
    start1, start2 = StartSentence(), StartSentence()
    end1, end2 = EndSentence(), EndSentence()

    def lookup_word(word_dict, word):
        canonical = Word.normalize_word(word)
        try:
            return word_dict[canonical]
        except KeyError:
            obj = Word()
            word_dict[canonical] = obj
            return obj

    msg_re = re.compile(r'\d{2}:\d{2} <(.*?)> (.*)')
    for line in logfile:
        m = msg_re.match(line)
        if m:
            nick, msg = m.groups()
            msg = msg.split()
            if nick == nick1:
                word_dict = words1
                start = start1
                end = end1
            elif nick == nick2:
                word_dict = words2
                start = start2
                end = end2
            else:
                continue

            for a, b in get_pairs(msg, start, end):
                word_a = lookup_word(word_dict, a)
                word_a.add(a)
                word_b = lookup_word(word_dict, b)
                word_b.add(b)
                word_a.add_next(word_b)

    return words1.values(), words2.values()



if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('--nick1', help='nick1')
    parser.add_option('--nick2', help='nick2')
    parser.add_option('-s', '--sleep', type='float', default=5.0)
    parser.add_option('-f', '--file', help='logfile')
    opts, args = parser.parse_args()

    if not opts.nick1:
        parser.error('must specify --nick1')
    if not opts.nick2:
        parser.error('must specify --nick2')
    if not opts.file:
        parser.error('must specify -f/--file')

    print 'parsing log...'
    with open(opts.file, 'r') as logfile:
        words1, words2 = build_adjacencies(opts.nick1, opts.nick2, logfile)
        word_lists = (words1, words2)

    print 'building probability matrix...'
    for wl in word_lists:
        for word in wl:
            word.construct_probabilities()

    def find_start(word_list):
        for word in word_list:
            if word.is_start:
                return word

    start1 = find_start(words1)
    start2 = find_start(words2)

    print 'chatting'
    i = 0
    while True:
        if i == 0:
            nick = opts.nick1
            words = words1
            start = start1
            i = 1
        else:
            nick = opts.nick2
            words = words2
            start = start2
            i = 0

        word = pick(start.probnext)
        sentence = []
        while not word.is_end:
            form = pick(word.probvar)
            sentence.append(form)
            word = pick(word.probnext)

        print '<%s> %s' % (nick, ' '.join(sentence))
        time.sleep(opts.sleep)
