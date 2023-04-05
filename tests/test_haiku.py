import pytest
from uqcsbot.haiku import (
    _number_of_syllables_in_word,
    _find_haiku
)


def test_number_of_syllables_in_word():
    test_cases = {
        "hello": 2,
        "ok": 2,
        "maybe": 2,
        "sentences": 3,
        "syllables": 3,
        "help": 1,
        "😄": 0,
        "help😄": 1,
        "help<:disapproval:1053481630037196931>": 1,
        "<:disapproval:1053481630037196931>": 0,
        "mis-fire": 2,
        "opportunity": 5
    }
    for (word, expected_syllable_count) in test_cases.items():
        assert _number_of_syllables_in_word(word) == expected_syllable_count


def test_find_haiku():
    true_cases = [
        "THOSE ARE THE EYES OF A MAN WHO SAW SATAN AND ASKED FOR HIS NUMBER",
        "NOPE, RELIES ON END OF SENTANCES THEN? MAYBE; BUT NOW SHOULD BE FIXD",
        "TEST AWAY STUDENTS; FIND SYLLABLES MISCOUNTED; LET ME FIX THE BUGS",
        "I AM ALL OUT OF HAIKUS ON THIS FINE MORNING GOOD LUCK WITH YOUR TESTS",
        "OK IT WORKS! MIGHT MIS-FIRE OCCASIONALLY, BUT EH... GOOD ENOUGH",
        "OK IT WORKS! MIGHT MIS-FIRE <:disapproval:1053481630037196931>  OCCASIONALLY, BUT EH... GOOD ENOUGH 😄",
        "OK IT WORKS! MIGHT MIS-FIRE<:disapproval:1053481630037196931>  OCCASIONALLY, BUT EH... GOOD ENOUGH 😄",
        "OK IT WORKS! 😄 MIGHT MIS-FIRE OCCASIONALLY, BUT EH... GOOD ENOUGH",
        "YOU WRITE A MESSAGE AND IT TURNS OUT TO BE A HAIKU AND YOU WIN"
    ]
    false_cases = [
        "This is not a haiku",
        "neither is this",
        "this is far too long to be a haiku, you should not accept this",
        "when a haiku; kinda fits but has a word; at the end too longer"
    ]
    for haiku in true_cases:
        assert haiku
    for text in false_cases:
        assert not haiku
