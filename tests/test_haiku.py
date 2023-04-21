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
        "resume": 2,
        "equal": 2,
        "unequal": 3,
        "BSOD": 4,
        "beverage": 3,
        "superior": 4,
        "islet": 2,
        "whitespace": 2,
        "uq": 2,
        "uqcs": 4,
        "accompanied": 4,
        "tried": 1,
        "tries": 1,
        "theyre": 1,
        "café": 2,
        "résumé": 3,
        "pâté": 2,
        "naïve": 2,
        "varied": 2,
        "career": 3,
        "preach": 1,
        "cried": 1,
        "tèst": 1,
        "poet": 2,
        "poetry": 3,
        "apostrophe": 4,
        "catastrophe": 4,
        "houses": 2,
        "beaches": 2,
        "batches": 2,
        "caches": 2,
        "clothes": 1,
        "breathes": 1,
        "class's": 2,
        "classes": 2,
        "that's": 1,
        "beach's": 2,
        "house's": 2,
        "test's": 1,
        "rash's": 2,
        "I": 1,
        "less": 1,
        "mess": 1,
        "ship": 1,
        "meant": 1,
        "messes": 2,
        "something": 2,
        "thing": 1,
        "bring": 1,
    }
    for (word, expected_syllable_count) in test_cases.items():
        assert _number_of_syllables_in_word(word) == expected_syllable_count


def test_find_haiku():
    # Many of these cases are from the discord itself (where the bot incorrectly failed before updates). Try to append the username when adding more test cases if the user agrees.
    true_cases = [
        "THOSE ARE THE EYES OF A MAN WHO SAW SATAN AND ASKED FOR HIS NUMBER",  # Anon.
        "NOPE, RELIES ON END OF SENTANCES THEN? MAYBE; BUT NOW SHOULD BE FIXD",  # indium#6908
        "TEST AWAY STUDENTS; FIND SYLLABLES MISCOUNTED; LET ME FIX THE BUGS",  # indium#6908
        "I AM ALL OUT OF HAIKUS ON THIS FINE MORNING GOOD LUCK WITH YOUR TESTS",  # </hax>#6701
        "OK IT WORKS! MIGHT MIS-FIRE OCCASIONALLY, BUT EH... GOOD ENOUGH",  # indium#6908
        "OK IT WORKS! MIGHT MIS-FIRE <:disapproval:1053481630037196931>  OCCASIONALLY, BUT EH... GOOD ENOUGH 😄",  # indium#6908
        "OK IT WORKS! MIGHT MIS-FIRE<:disapproval:1053481630037196931>  OCCASIONALLY, BUT EH... GOOD ENOUGH 😄",  # indium#6908
        "OK IT WORKS! 😄 MIGHT MIS-FIRE OCCASIONALLY, BUT EH... GOOD ENOUGH",  # indium#6908
        "YOU WRITE A MESSAGE AND IT TURNS OUT TO BE A HAIKU AND YOU WIN",  # indium#6908
        "contractions are hard because they break a lot of the syllabic rules",  # </hax>#6701
        "I'm going to write the lowest effort haiku imaginable",  # enchi#8880
        "Yea, true. That's quite a good point that I had not quite thought of. Very true",
        "ill have to become careful with my messages to not send haiku",  # miri#2222
        "fwiw you also have to have word breaks in the right places to make it 5/7/5",  # </hax>#6701
        "This is a haiku\n I just want to test the bot\n Didn't read the code",  # NotRealAqua#6969
        "hot chocolate is clearly the superior beverage though lol",  # Madeline#8084
        "pretty sure it's the immune system attacking beta islet cells",  # Madeline#8084
        "wow I can't believe that it's haiku poetry day already guys",  # enchi#8880
        "Rhyme's overrated Haikus\n let you have some fun\n Plus they have good tune",  # NotRealAqua#6969
        "I could tell you more\n But with less words or lots more\n And you would feel them",  # Anti-Matter#1740
        "Random syllables?\n Perhaps we need more Lovecraft\n Really random tongue",
        "something blah blah blah\n insert random words right here\n blah blah blah deez nuts",
    ]
    false_cases = [
        "This is not a haiku",  # indium#6908
        "neither is this",  # indium#6908
        "this is far too long to be a haiku, you should not accept this",  # indium#6908
        "when a haiku; kinda fits but has a word; at the end too longer",  # indium#6908
        "ive tried these as emergency \"feed me now\" meals and theyre so bland",  # villuna#6251
        "Lovecraft my dear\n The bot is well confused\n Stop confusing it",
    ]
    for haiku in true_cases:
        assert _find_haiku(haiku)
    for text in false_cases:
        assert not _find_haiku(text)
