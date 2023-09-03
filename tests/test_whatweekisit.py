from datetime import datetime
import pytest
import os

from uqcsbot.whatweekisit import (
    get_semester_times,
    get_semester_week,
    date_to_string,
    string_to_date,
)


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "testfiles",
)


@pytest.mark.datafiles(os.path.join(FIXTURE_DIR, "test_whatweekisit.html"))
def test_get_semester_times_from_file(datafiles):
    with open(
        os.path.join(datafiles, "test_whatweekisit.html"), "r", encoding="utf-8"
    ) as f:
        hardcoded_file = f.read()

    # We can manually look at the HTML document to see if this is accurate
    semesters = get_semester_times(hardcoded_file)

    semester_one, semester_two = semesters
    assert semester_one.name == "First Semester, 2022"
    assert date_to_string(semester_one.start_date) == "14/02/2022"
    assert date_to_string(semester_one.end_date) == "21/06/2022"
    assert len(semester_one.weeks) == 19

    assert semester_two.name == "Second Semester, 2022"
    assert date_to_string(semester_two.start_date) == "18/07/2022"
    assert date_to_string(semester_two.end_date) == "20/11/2022"
    assert len(semester_two.weeks) == 18


@pytest.mark.datafiles(os.path.join(FIXTURE_DIR, "test_whatweekisit.html"))
def test_get_semester_week_from_file(datafiles):
    with open(
        os.path.join(datafiles, "test_whatweekisit.html"), "r", encoding="utf-8"
    ) as f:
        hardcoded_file = f.read()

    # Get semesters so we can then get the week from it
    semesters = get_semester_times(hardcoded_file)

    # Check few different instances
    second_sem_week_one_day_two = string_to_date("26/07/2022")
    semester_tuple = get_semester_week(semesters, second_sem_week_one_day_two)
    assert semester_tuple is not None

    _, week_name, weekday = semester_tuple
    assert week_name == "Week 1"
    assert weekday == "Tuesday"

    second_sem_break_day_four = string_to_date("29/09/2022")
    semester_tuple = get_semester_week(semesters, second_sem_break_day_four)
    assert semester_tuple is not None

    _, week_name, weekday = semester_tuple
    assert week_name == "Break Week"
    assert weekday == "Thursday"
