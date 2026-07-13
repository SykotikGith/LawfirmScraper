from .base import Adapter
from .icims import ICIMSAdapter
from .workday import WorkdayAdapter
from .applicantstack import ApplicantStackAdapter
from .oracle import OracleRecruitingAdapter
from .custom_html import CustomHTMLAdapter
from .greenhouse import GreenhouseAdapter
from .circaworks import CircaWorksAdapter
from .viglobal import ViGlobalAdapter
from .ultipro import UltiProAdapter
from .earcu import EArcuAdapter
from .jobvite import JobviteAdapter

__all__ = [
    "Adapter",
    "ICIMSAdapter",
    "WorkdayAdapter",
    "ApplicantStackAdapter",
    "OracleRecruitingAdapter",
    "CustomHTMLAdapter",
    "GreenhouseAdapter",
    "CircaWorksAdapter",
    "ViGlobalAdapter",
    "UltiProAdapter",
    "EArcuAdapter",
    "JobviteAdapter",
]
