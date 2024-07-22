import requests
from requests.exceptions import RequestException
from datetime import datetime
from dateutil import parser
from bs4 import BeautifulSoup, element
from typing import Optional, Literal
from dataclasses import dataclass
import json
import re

BASE_COURSE_URL = "https://my.uq.edu.au/programs-courses/course.html?course_code="
BASE_ASSESSMENT_URL = (
    "https://www.courses.uq.edu.au/"
    "student_section_report.php?report=assessment&profileIds="
)
BASE_CALENDAR_URL = "http://www.uq.edu.au/events/calendar_view.php?category_id=16&year="
BASE_PAST_EXAMS_URL = "https://api.library.uq.edu.au/v1/exams/search/"
# Parameters for the course page
OFFERING_PARAMETER = "offer"
YEAR_PARAMETER = "year"


class Offering:
    """
    A semester, campus and mode (e.g. Internal) that many courses occur within
    """

    CampusType = Literal["St Lucia", "Gatton", "Herston"]
    # The codes used internally within UQ systems
    campus_codes: dict[CampusType, str] = {
        "St Lucia": "STLUC",
        "Gatton": "GATTN",
        "Herston": "HERST",
    }

    ModeType = Literal["Internal", "External", "Flexible Delivery", "Intensive"]
    # The codes used internally within UQ systems
    mode_codes: dict[ModeType, str] = {
        "Internal": "IN",
        "External": "EX",
        "Flexible Delivery": "FD",
        "Intensive": "IT",
    }

    SemesterType = Literal["1", "2", "Summer"]
    semester_codes: dict[SemesterType, int] = {"1": 1, "2": 2, "Summer": 3}

    semester: SemesterType
    campus: CampusType
    mode: ModeType

    def __init__(
        self,
        semester: Optional[SemesterType],
        campus: CampusType = "St Lucia",
        mode: ModeType = "Internal",
    ):
        """
        semester defaults to the current semester if None
        """
        if semester is not None:
            self.semester = semester
        else:
            self.semester = self.estimate_current_semester()
        self.semester
        self.campus = campus
        self.mode = mode

    def get_semester_code(self) -> int:
        """
        Returns the code used interally within UQ for the semester of the offering.
        """
        return self.semester_codes[self.semester]

    def get_campus_code(self) -> str:
        """
        Returns the code used interally within UQ for the campus of the offering.
        """
        self.campus
        return self.campus_codes[self.campus]

    def get_mode_code(self) -> str:
        """
        Returns the code used interally within UQ for the mode of the offering.
        """
        return self.mode_codes[self.mode]

    def get_offering_code(self) -> str:
        """
        Returns the hex encoded offering string (containing all offering information) for the offering.
        """
        offering_code_text = (
            f"{self.get_campus_code()}{self.get_semester_code()}{self.get_mode_code()}"
        )
        return offering_code_text.encode("utf-8").hex()

    @staticmethod
    def estimate_current_semester() -> SemesterType:
        """
        Returns an estimate of the current semester (represented by an integer) based on the current month. 3 represents summer semester.
        """
        current_month = datetime.today().month
        if 2 <= current_month <= 6:
            return "1"
        elif 7 <= current_month <= 11:
            return "2"
        else:
            return "Summer"


@dataclass
class AssessmentItem:
    course_name: str
    category: str
    task: str
    task_details_url: str
    due_date: str  # This often also contains a lot of description
    weight: str

    def get_parsed_due_date(self) -> Optional[tuple[datetime, datetime]]:
        """
        Returns the parsed due date for the given assessment item as a datetime
        object. If the date cannot be parsed, a DateSyntaxException is raised.
        """
        if self.due_date.startswith("End of Semester Exam Period"):
            return get_current_exam_period()
        parser_info = parser.parserinfo(dayfirst=True)
        potential_date_strings: list[str] = re.findall(
            r"\d\d?/\d\d?/\d\d\d\d( \d\d?(:\d\d)?( [ap]m)?)?", self.due_date
        )
        dates: list[datetime] = []

        for potential_date_string in potential_date_strings:
            try:
                date = parser.parse(potential_date_string, parser_info)
                dates.append(date)
            except Exception:
                # No need to do anything if the date cannot be parsed
                pass

        if dates:
            return min(dates), max(dates)
        return None

    def is_after(self, cutoff: datetime):
        """
        Returns whether the assessment occurs after the given cutoff.
        """
        date_range = self.get_parsed_due_date()
        if date_range is None:
            # If we can't parse a date, we're better off keeping it just in case.
            return True

        _, end_datetime = date_range
        return end_datetime >= cutoff

    def is_before(self, cutoff: datetime):
        """
        Returns whether the assessment occurs before the given cutoff.
        """
        date_range = self.get_parsed_due_date()
        if date_range is None:
            # If we can't parse a date, we're better off keeping it just in case.
            return True

        start_datetime, _ = date_range
        return start_datetime <= cutoff

    def get_weight_as_int(self) -> Optional[int]:
        """
        Trys to get the weight percentage of an assessment as a percentage. Will return None
        if a percentage can not be obtained.
        """
        if match := re.match(r"\d+", self.weight):
            return int(match.group(0))
        return None


class CourseNotFoundException(Exception):
    """
    Raised when a given course cannot be found for UQ.
    """

    def __init__(self, course_name: str):
        self.message = f"Could not find course '{course_name}'."
        self.course_name = course_name
        super().__init__(self.message, self.course_name)


class ProfileNotFoundException(Exception):
    """
    Raised when a profile cannot be found for a given course.
    """

    def __init__(self, course_name: str, offering: Optional[Offering] = None):
        if offering is None:
            self.message = f"Could not find profile for course '{course_name}'. This profile may not be out yet."
        else:
            self.message = f"Could not find profile for course '{course_name}' during semester {offering.semester} at {offering.campus} done in mode '{offering.mode}'. This profile may not be out yet."
        self.course_name = course_name
        self.offering = offering
        super().__init__(self.message, self.course_name, self.offering)


class AssessmentNotFoundException(Exception):
    """
    Raised when the assessment table cannot be found for assess page.
    """

    def __init__(self, course_name: str, offering: Optional[Offering] = None):
        if offering is None:
            self.message = f"Could not find the assessment table for '{course_name}'."
        else:
            self.message = f"Could not find the assessment table for '{course_name}' during semester {offering.semester} at {offering.campus} done in mode '{offering.mode}'."
        self.course_name = course_name
        super().__init__(self.message, self.course_name)


class AssessmentNotParseableException(Exception):
    """
    Raised when the assessment cannot be parsed from the ECP.
    """

    def __init__(self, course_name: str, course_profile_url: str):
        self.message = (
            f"Could not parse an assessment for '{course_name}': {course_profile_url}"
        )
        self.course_name = course_name
        self.course_profile_url = course_profile_url
        super().__init__(self.message, self.course_name)


class HttpException(Exception):
    """
    Raised when a HTTP request returns an
    unsuccessful (i.e. not 200 OK) status code.
    """

    def __init__(self, url: str, status_code: int):
        self.message = f"Received status code {status_code} from '{url}'."
        self.url = url
        self.status_code = status_code
        super().__init__(self.message, self.url, self.status_code)


def get_uq_request(
    url: str, params: Optional[dict[str, str]] = None
) -> requests.Response:
    """
    Handles specific error handelling and header provision for requests.get to
    uq course urls
    """
    headers = {"User-Agent": "UQCS"}
    try:
        return requests.get(url, params=params, headers=headers)
    except RequestException as ex:
        # For some reason this is the most specific exception for the
        # "http.client.RemoteDisconnected: Remote end closed connection without
        # response" exception, return a more useful error
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        raise HttpException(message, 500)


def get_course_profile_url(
    course_name: str,
    offering: Optional[Offering] = None,
    year: Optional[int] = None,
) -> str:
    """
    Returns the URL to the course profile (ECP) for the given course for a given offering.
    If no offering or year are given, the first course profile on the course page will be returned.
    """
    course_url = BASE_COURSE_URL + course_name
    if offering:
        course_url += "&" + OFFERING_PARAMETER + "=" + offering.get_offering_code()
    if year:
        course_url += "&" + YEAR_PARAMETER + "=" + str(year)

    http_response = get_uq_request(course_url)
    if http_response.status_code != requests.codes.ok:
        raise HttpException(course_url, http_response.status_code)
    html = BeautifulSoup(http_response.content, "html.parser")
    if html.find(id="course-notfound"):
        raise CourseNotFoundException(course_name)

    if offering is None:
        profile = html.find("a", class_="profile-available")
    else:
        # The profile row on the course page that corresponds to the given offering
        table_row = html.find("tr", class_="current")
        if not isinstance(table_row, element.Tag):
            raise ProfileNotFoundException(course_name, offering)
        profile = table_row.find("a", class_="profile-available")

    if not isinstance(profile, element.Tag):
        raise ProfileNotFoundException(course_name, offering)
    url = profile.get("href")
    if not isinstance(url, str):
        raise ProfileNotFoundException(course_name, offering)
    return url


def get_current_exam_period():
    """
    Returns the start and end datetimes for the current semester's exam period.

    Note: Assumes that Semester 1 always occurs before or
    during June, with Semester 2 occurring after.
    """
    today = datetime.today()
    current_calendar_url = BASE_CALENDAR_URL + str(today.year)
    http_response = get_uq_request(current_calendar_url)
    if http_response.status_code != requests.codes.ok:
        raise HttpException(current_calendar_url, http_response.status_code)
    html = BeautifulSoup(http_response.content, "html.parser")
    event_date_elements = html.findAll("li", class_="description-calendar-view")
    event_date_texts = [element.text for element in event_date_elements]
    current_semester = "1" if today.month <= 6 else "2"
    exam_snippet = f"Semester {current_semester} examination period "
    # The first event encountered is the one which states the commencement of
    # the current semester's exams and also provides the exam period.
    exam_date_text = [t for t in event_date_texts if exam_snippet in t][0]
    start_day, end_date = exam_date_text[len(exam_snippet) :].split(" - ")
    end_datetime = parser.parse(end_date)
    start_datetime = end_datetime.replace(day=int(start_day))
    return start_datetime, end_datetime


def get_course_assessment(
    course_name: str,
    offering: Offering,
) -> list[AssessmentItem]:
    """
    Returns all the assessment for the given
    course that occur after the given cutoff.
    """
    course_profile_url = get_course_profile_url(course_name, offering=offering)
    course_assessment_url = course_profile_url + "#assessment"

    http_response = get_uq_request(course_assessment_url)
    if http_response.status_code != requests.codes.ok:
        raise HttpException(course_assessment_url, http_response.status_code)
    html = BeautifulSoup(http_response.content, "html.parser")

    assessment_table = html.find("div", class_="assessment-summary-table")
    if not isinstance(assessment_table, element.Tag):
        raise AssessmentNotFoundException(course_name, offering)
    # Start from 1st index to skip over the row containing column names.
    assessment_table = assessment_table.findAll("tr")[1:]
    return [
        get_parsed_assessment_item(row, course_name, course_profile_url)
        for row in assessment_table
    ]


def get_element_inner_html(dom_element: element.Tag):
    """
    Returns the inner html for the given element.
    """
    return dom_element.decode_contents(formatter="html")


def get_parsed_assessment_item(
    assessment_item_tag: element.Tag, course_name: str, course_profile_url: str
) -> AssessmentItem:
    """
    Returns the parsed assessment details for the
    given assessment item table row element in the ECP.
    """
    assessment_cells: element.ResultSet[element.Tag] = assessment_item_tag.findAll("td")
    category, task, weight, due_date = assessment_cells

    category = category.text.strip()

    task = task.findChild("a")
    if not isinstance(task, element.Tag):
        raise AssessmentNotParseableException(course_name, course_profile_url)
    task_description_url = course_profile_url + task.attrs["href"]
    task = task.text.strip()

    weight = weight.text.strip()

    due_date_paragraphs: element.ResultSet[element.Tag] = due_date.findAll("p")
    due_date_lines = (p.text.strip() for p in due_date_paragraphs)
    due_date = "\n".join(line for line in due_date_lines if line)

    return AssessmentItem(
        course_name, category, task, task_description_url, due_date, weight
    )


class Exam:
    """
    Stores the information of a past exam, including its year, semester and link.
    """

    def __init__(self, year: int, semester: str, link: str) -> None:
        self.year = year
        self.semester = semester
        self.link = link


def get_past_exams_page_url(course_code: str) -> str:
    """
    Returns the URL of the UQ library past exam page
    """
    return BASE_PAST_EXAMS_URL + course_code


def get_past_exams(course_code: str) -> list[Exam]:
    """
    Takes the course code and generates each result in the format:
    ('year Sem X:', link)
    """
    url = get_past_exams_page_url(course_code)
    http_response = requests.get(url)
    if http_response.status_code != requests.codes.ok:
        raise HttpException(url, http_response.status_code)
    # The UQ library API has some funky nested lists within the output, so there will be a a few "[0]" lying about
    exam_list_json = json.loads(http_response.content)["papers"]

    # Check if the course code exists
    if not exam_list_json:
        return []
    exam_list_json = exam_list_json[0]

    exam_list: list[Exam] = []
    for exam_json in exam_list_json:
        year = int(exam_json[0]["examYear"])
        # Semesters are given as "Sem.1", so we will change this to "Sem 1"
        semester = exam_json[0]["examPeriod"].replace(".", " ")
        link = exam_json[0]["paperUrl"]
        exam_list.append(Exam(year, semester, link))
    return exam_list
