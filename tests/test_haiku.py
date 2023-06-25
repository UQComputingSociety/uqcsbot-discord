import pytest
from uqcsbot.haiku import _number_of_syllables_in_word, _find_haiku


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
        "B-T-W": 3,
        "someone's": 2,
        "something's": 2,
        "biped": 2,
        "daybed": 2,
        "bed": 1,
        "jaded": 2,
        "naked": 2,
        "parallelepiped": 6,
        "science": 2,
        "scitech": 2,
        "scienergy": 4,
        "baked": 1,
        "wiped": 1,
        "sniped": 1,
        "griped": 1,
        "therefore": 2,
        "theremin": 3,
        "forefather": 3,
        "abalone": 4,
        "marscapone": 4,
        "everyone": 3,
        "wretched": 2,
        "react": 2,
        "reach": 1,
        "read": 1,
        "ready": 2,
        "readdress": 3,
        "readjustment": 4,
        "reached": 1,
        "reachable": 3,
        "reaches": 2,
        "reaching": 2,
        "react": 2,
        "reaction": 3,
        "reader": 2,
        "readership": 3,
        "reading": 2,
        "readiness": 3,
        "readily": 3,
        "ready": 2,
        "reaffirm": 3,
        "real": 1,
        "realignment": 4,
        "realisation": 4,
        "realised": 2,
        "realism": 3,
        "realistic": 3,
        "realistically": 5,
        "really": 2,
        "reality": 4,
        "realign": 3,
        "realm": 1,
        "reallocation": 5,
        "realtor": 2,
        "realities": 4,
        "reap": 1,
        "reapply": 3,
        "reappear": 3,
        "reappointment": 4,
        "rearm": 2,
        "rearrangement": 4,
        "rearrest": 3,
        "reason": 2,
        "reasonable": 4,
        "reasonably": 4,
        "reassess": 3,
        "reassesses": 4,
        "reassurance": 4,
        "reed": 1,
        "reeducation": 5,
        "reef": 1,
        "reel": 1,
        "reelection": 4,
        "reeling": 2,
        "reich": 1,
        "reign": 1,
        "reignite": 3,
        "reimagine": 4,
        "reimburse": 3,
        "reindeer": 2,
        "rein": 2,
        "reinforce": 3,
        "reinstate": 3,
        "reinvent": 3,
        "reissue": 3,
        "reiterate": 4,
        "reopen": 3,
        "reorganise": 4,
        "reorganisation": 6,
        "reunion": 3,
        "reunite": 3,
        "reuse": 2,
        "reuter": 2,
        "plier": 2,
        "plied": 1,
        "pliant": 2,
        "pliable": 3,
        "plies": 1,
        "reliable": 4,
        "agreed": 2,
        "accrued": 2,
        "segue": 2,
        "segued": 2,
        "imbued": 2,
        "silhouette": 3,
        "epitome": 4,
        "forte": 2,
        "daybed": 2,
        "jaded": 2,
        "naked": 2,
        "resume": 2,
        "biped": 2,
        "anyone": 3,
        "schism": 2,
        "less": 1,
        "mist": 1,
        "fish": 1,
        "Wostershire": 3,
        "Frappe": 2,
        "livestream": 2,
        "pikelet": 2,
        "meringue": 2,
        "vague": 1,
        "any": 2,
        "video": 3,
        "area": 3,
        "media": 3,
        "previous": 3,
        "experience": 4,
        "audio": 3,
        "areas": 3,
        "radio": 3,
        "safety": 2,
        "association": 5,
        "period": 3,
        "style": 1,
        "centre": 2,
        "via": 2,
        "videos": 3,
        "player": 2,
        "india": 3,
        "created": 3,
        "abusing": 3,
        "acne": 2,
        "acquire": 2,
        "accompaniment": 5,
        "amusing": 3,
        "rhythm": 2,
        "mario": 3,
        "punctuation": 4,
        "variation": 4,
        "ivy": 2,
        "era": 2,
        "metre": 2,
        "slayer": 2,
        "create": 2,
        "algorithm": 4,
        "the": 1,
    }
    for word, expected_syllable_count in test_cases.items():
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
        "Random syllables?\n Perhaps we need more Lovecraft\n Really random tongue",  # lsenjov#4288 
        "something blah blah blah\n insert random words right here\n blah blah blah deez nuts",  # numberri#4096
    ]
    false_cases = [
        "This is not a haiku",  # indium#6908
        "neither is this",  # indium#6908
        "this is far too long to be a haiku, you should not accept this",  # indium#6908
        "when a haiku; kinda fits but has a word; at the end too longer",  # indium#6908
        "ive tried these as emergency \"feed me now\" meals and theyre so bland",  # villuna#6251
        "Lovecraft my dear\n The bot is well confused\n Stop confusing it",  # lsenjov#4288
        "someone's getting it sooner and someone's getting it later :^)",  # Madeline#8084
        "socially inept people? in MY computer science discord server", # miri#2222
    ]
    for haiku in true_cases:
        is_haiku, _ = _find_haiku(haiku)
        assert is_haiku
    for text in false_cases:
        is_haiku, _ = _find_haiku(text)
        assert not is_haiku
