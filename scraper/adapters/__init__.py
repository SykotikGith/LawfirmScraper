from .base import Adapter
from .icims import ICIMSAdapter
from .workday import WorkdayAdapter
from .applicantstack import ApplicantStackAdapter
from .oracle import OracleRecruitingAdapter
from .custom_html import CustomHTMLAdapter

__all__ = [
    "Adapter",
    "ICIMSAdapter",
    "WorkdayAdapter",
    "ApplicantStackAdapter",
    "OracleRecruitingAdapter",
    "CustomHTMLAdapter",
]
