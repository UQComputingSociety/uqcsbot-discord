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
        "syllable": 3,
        "syllablic": 3,
        "help": 1,
        "😄": 0,
        "help😄": 1,
        "help<:disapproval:1053481630037196931>": 1,
        "<:disapproval:1053481630037196931>": 0,
        "mis-fire": 2,
        "opportunity": 5,
        "acted": 2,
        "flipped": 1,
        "asked": 1,
        "boreal": 3,
        "cereal": 3,
        "corneal": 3,
        "ethereal": 4,
        "montreal": 3,
        "real": 1,
        "apple": 2,
        "apples": 2,
        "whale": 1,
        "whales": 1,
        "whole": 1,
        "anxious": 2,
        "amphibious": 4,
        "harmonious": 4,
        "copious": 3,
        "glorious": 3,
        "initial": 3,
        "microbial": 4,
        "radial": 3,
        "polynomial": 5,
        "millennial": 4,
        "aerial": 3,
        "trivial": 3,
        "axial": 3,
        "contextual": 4,
        "actual": 3,
        "casual": 3,
        "usual": 3,
        "actually": 4,
        "casually": 4,
        "usually": 4,
        "triangle": 3,
        "biology": 4,
        "Australian": 4,
        "politician": 4,
        "coincidence": 4,
        "preamble": 3,
        "preempt": 2,
        "dual": 2,
        "eyes": 1,
        "ageless": 2,
        "manly": 2,
        "didn't": 2,
        "doesn't": 2,
        "wouldn't": 2,
        "couldn't": 2,
        "shouldn't": 2,
        "isn't": 2,
        "don't": 1,
        "didnt": 2,
        "doesnt": 2,
        "wouldnt": 2,
        "couldnt": 2,
        "shouldnt": 2,
        "isnt": 2,
        "dont": 1,
        "contractions": 3,
        "are": 1,
        "because": 2,
        "rules": 1,
        "cages": 2,
        "cafes": 2,
        "going": 2,
        "skiing": 2,
        "ageism": 3,
        "antidisestablishmentarianism": 12,
        "every": 2,
        "graduate": 3,
        "differentiate": 5,
        "graduate": 3,
        "create": 2,
        "naive": 2,
        "date": 1,
        "crate": 1,
        "resume": 3,
        "equal": 2,
        "unequal": 3,
        "BSOD": 4,
        "beverage": 3,
        "superior": 4,
        "islet": 2,
    }
    for (word, expected_syllable_count) in test_cases.items():
        assert _number_of_syllables_in_word(word) == expected_syllable_count


def test_find_haiku():
    # Many of these cases are from the discord itself (where the bot incorrectly failed before updates). Try to append the username when adding more test cases if the user agrees.
    true_cases = [
        "THOSE ARE THE EYES OF A MAN WHO SAW SATAN AND ASKED FOR HIS NUMBER",
        "NOPE, RELIES ON END OF SENTANCES THEN? MAYBE; BUT NOW SHOULD BE FIXD",  # indium#6908
        "TEST AWAY STUDENTS; FIND SYLLABLES MISCOUNTED; LET ME FIX THE BUGS",  # indium#6908
        "I AM ALL OUT OF HAIKUS ON THIS FINE MORNING GOOD LUCK WITH YOUR TESTS",  # </hax>#6701
        "OK IT WORKS! MIGHT MIS-FIRE OCCASIONALLY, BUT EH... GOOD ENOUGH",  # indium#6908
        "OK IT WORKS! MIGHT MIS-FIRE <:disapproval:1053481630037196931>  OCCASIONALLY, BUT EH... GOOD ENOUGH 😄",  # indium#6908
        "OK IT WORKS! MIGHT MIS-FIRE<:disapproval:1053481630037196931>  OCCASIONALLY, BUT EH... GOOD ENOUGH 😄",  # indium#6908
        "OK IT WORKS! 😄 MIGHT MIS-FIRE OCCASIONALLY, BUT EH... GOOD ENOUGH",  # indium#6908
        "YOU WRITE A MESSAGE AND IT TURNS OUT TO BE A HAIKU AND YOU WIN",  # indium#6908
        "contractions are hard because they break a lot of the syllabic rules",  # </hax>#6701
        "I'm going to write the lowest effort haiku imaginable",  # NotRealAqua#6969
        "Yea, true. That's quite a good point that I had not quite thought of. Very true",
        "ill have to become careful with my messages to not send haiku",  # miri#2222
        "fwiw you also have to have word breaks in the right places to make it 5/7/5",  # </hax>#6701
        "This is a haiku\n I just want to test the bot\n Didn't read the code",  # NotRealAqua#6969
        "hot chocolate is clearly the superior beverage though lol",  # Madeline#8084
        "pretty sure it's the immune system attacking beta islet cells",  # Madeline#8084
    ]
    false_cases = [
        "This is not a haiku",
        "neither is this",
        "this is far too long to be a haiku, you should not accept this",
        "when a haiku; kinda fits but has a word; at the end too longer",
    ]
    for haiku in true_cases:
        assert _find_haiku(haiku)
    for text in false_cases:
        assert not _find_haiku(text)
