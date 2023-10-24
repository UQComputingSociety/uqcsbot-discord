import requests
from requests.exceptions import RequestException
from datetime import datetime
from dateutil import parser
from bs4 import BeautifulSoup, element
from functools import partial
from typing import List, Dict, Optional, Literal, Tuple
import json

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
    campus_codes: Dict[CampusType, str] = {
        "St Lucia": "STLUC",
        "Gatton": "GATTN",
        "Herston": "HERST",
    }

    ModeType = Literal["Internal", "External", "Flexible Delivery", "Intensive"]
    # The codes used internally within UQ systems
    mode_codes: Dict[ModeType, str] = {
        "Internal": "IN",
        "External": "EX",
        "Flexible Delivery": "FD",
        "Intensive": "IT",
    }

    SemesterType = Literal["1", "2", "Summer"]
    semester_codes: Dict[SemesterType, int] = {"1": 1, "2": 2, "Summer": 3}

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
            self.semester = self._estimate_current_semester()
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
    def _estimate_current_semester() -> SemesterType:
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


class DateSyntaxException(Exception):
    """
    Raised when an unparsable date syntax is encountered.
    """

    def __init__(self, date: str, course_name: str):
        self.message = f"Could not parse date '{date}' for course '{course_name}'."
        self.date = date
        self.course_name = course_name
        super().__init__(self.message, self.date, self.course_name)


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

    def __init__(self, course_names: List[str], offering: Optional[Offering] = None):
        if offering is None:
            self.message = (
                f"Could not find the assessment table for '{', '.join(course_names)}'."
            )
        else:
            self.message = f"Could not find the assessment table for '{', '.join(course_names)}' during semester {offering.semester} at {offering.campus} done in mode '{offering.mode}'."
        self.course_names = course_names
        super().__init__(self.message, self.course_names)


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
    url: str, params: Optional[Dict[str, str]] = None
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
    course_name: str, offering: Optional[Offering] = None, year: Optional[int] = None,
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


def get_course_profile_id(course_name: str, offering: Optional[Offering]):
    """
    Returns the ID to the latest course profile for the given course.
    """
    profile_url = get_course_profile_url(course_name, offering=offering)
    # The profile url looks like this
    # https://course-profiles.uq.edu.au/student_section_loader/section_1/100728
    return profile_url[profile_url.rindex("/") + 1 :]


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


def get_parsed_assessment_due_date(assessment_item: Tuple[str, str, str, str]):
    """
    Returns the parsed due date for the given assessment item as a datetime
    object. If the date cannot be parsed, a DateSyntaxException is raised.
    """
    course_name, _, due_date, _ = assessment_item
    if due_date == "Examination Period":
        return get_current_exam_period()
    parser_info = parser.parserinfo(dayfirst=True)
    try:
        # If a date range is detected, attempt to split into start and end
        # dates. Else, attempt to just parse the whole thing.
        if " - " in due_date:
            start_date, end_date = due_date.split(" - ", 1)
            start_datetime = parser.parse(start_date, parser_info)
            end_datetime = parser.parse(end_date, parser_info)
            return start_datetime, end_datetime
        due_datetime = parser.parse(due_date, parser_info)
        return due_datetime, due_datetime
    except Exception:
        raise DateSyntaxException(due_date, course_name)


def is_assessment_after_cutoff(assessment: Tuple[str, str, str, str], cutoff: datetime):
    """
    Returns whether the assessment occurs after the given cutoff.
    """
    try:
        start_datetime, end_datetime = get_parsed_assessment_due_date(assessment)
    except DateSyntaxException:
        # TODO bot.logger.error(e.message)
        # If we can't parse a date, we're better off keeping it just in case.
        # TODO(mitch): Keep track of these instances to attempt to accurately
        # parse them in future. Will require manual detection + parsing.
        return True
    return end_datetime >= cutoff if end_datetime else start_datetime >= cutoff


def get_course_assessment_page(
    course_names: List[str], offering: Optional[Offering]
) -> str:
    """
    Determines the course ids from the course names and returns the
    url to the assessment table for the provided courses
    """
    profile_ids = map(
        lambda course: get_course_profile_id(course, offering=offering), course_names
    )
    return BASE_ASSESSMENT_URL + ",".join(profile_ids)


def get_course_assessment(
    course_names: List[str],
    cutoff: Optional[datetime] = None,
    assessment_url: Optional[str] = None,
    offering: Optional[Offering] = None,
) -> List[Tuple[str, str, str, str]]:
    """
    Returns all the course assessment for the given
    courses that occur after the given cutoff.
    """
    if assessment_url is None:
        joined_assessment_url = get_course_assessment_page(course_names, offering)
    else:
        joined_assessment_url = assessment_url
    http_response = get_uq_request(joined_assessment_url)
    if http_response.status_code != requests.codes.ok:
        raise HttpException(joined_assessment_url, http_response.status_code)
    html = BeautifulSoup(http_response.content, "html.parser")
    assessment_table = html.find("table", class_="tblborder")
    if not isinstance(assessment_table, element.Tag):
        raise AssessmentNotFoundException(course_names, offering)
    # Start from 1st index to skip over the row containing column names.
    assessment = assessment_table.findAll("tr")[1:]
    parsed_assessment = map(get_parsed_assessment_item, assessment)
    # If no cutoff is specified, set cutoff to UNIX epoch (i.e. filter nothing).
    cutoff = cutoff or datetime.min
    assessment_filter = partial(is_assessment_after_cutoff, cutoff=cutoff)
    filtered_assessment = filter(assessment_filter, parsed_assessment)
    return list(filtered_assessment)


def get_element_inner_html(dom_element: element.Tag):
    """
    Returns the inner html for the given element.
    """
    return dom_element.decode_contents(formatter="html")


def get_parsed_assessment_item(
    assessment_item: element.Tag,
) -> Tuple[str, str, str, str]:
    """
    Returns the parsed assessment details for the
    given assessment item table row element.

    Note: Because of the inconsistency of UQ assessment details, I've had to
    make some fairly strict assumptions about the structure of each field.
    This is likely insufficient to handle every course's
    structure, and thus is subject to change.
    """
    course_name, task, due_date, weight = assessment_item.findAll("div")
    # Handles courses of the form 'CSSE1001 - Sem 1 2018 - St Lucia - Internal'.
    # Thus, this bit of code will extract the course.
    course_name = course_name.text.strip().split(" - ")[0]
    # Handles tasks of the form 'Computer Exercise<br/>Assignment 2'.
    task = get_element_inner_html(task).strip().replace("<br/>", " - ")
    # Handles due dates of the form '26 Mar 18 - 27 Mar 18<br/>Held in Week 6
    # Learning Lab Sessions (Monday/Tuesday)'. Thus, this bit of code will
    # keep only the date portion of the field.
    due_date = get_element_inner_html(due_date).strip().split("<br/>")[0]
    # Handles weights of the form '30%<br/>Alternative to oral presentation'.
    # Thus, this bit of code will keep only the weight portion of the field.
    weight = get_element_inner_html(weight).strip().split("<br/>")[0]
    return (course_name, task, due_date, weight)


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


def get_past_exams(course_code: str) -> List[Exam]:
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

    exam_list: List[Exam] = []
    for exam_json in exam_list_json:
        year = int(exam_json[0]["examYear"])
        # Semesters are given as "Sem.1", so we will change this to "Sem 1"
        semester = exam_json[0]["examPeriod"].replace(".", " ")
        link = exam_json[0]["paperUrl"]
        exam_list.append(Exam(year, semester, link))
    return exam_list
