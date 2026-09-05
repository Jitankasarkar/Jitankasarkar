import base64
import json
import os
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

USERNAME = "Jitankasarkar"

API_URL = "https://api.github.com"

OUTPUT = Path("assets/github-dashboard.svg")

TOKEN = os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    raise RuntimeError("GITHUB_TOKEN is not available.")


# ============================================================
# GITHUB API HELPERS
# ============================================================

def github_get(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Jitanka-GitHub-Profile"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def github_graphql(query, variables):
    body = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "Jitanka-GitHub-Profile"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise RuntimeError(
            json.dumps(result["errors"], indent=2)
        )

    return result["data"]


# ============================================================
# TECHNOLOGY ICONS
#
# Devicon SVGs are downloaded and their SVG contents are
# embedded directly inside the generated dashboard.
# ============================================================

ICON_URLS = {
    "Java":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/java/java-original.svg",

    "Python":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/python/python-original.svg",

    "C":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/c/c-original.svg",

    "JavaScript":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/javascript/javascript-original.svg",

    "React":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/react/react-original.svg",

    "Flutter":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/flutter/flutter-original.svg",

    "Node.js":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/nodejs/nodejs-original.svg",

    "Express.js":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/express/express-original.svg",

    "Firebase":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/firebase/firebase-plain.svg",

    "MySQL":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/mysql/mysql-original.svg",

    "Git":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/git/git-original.svg",

    "GitHub":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/github/github-original.svg",

    "PyTorch":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/pytorch/pytorch-original.svg",

    "OpenCV":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/opencv/opencv-original.svg",

    "n8n":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/n8n/n8n-original.svg",

    "Postman":
        "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/postman/postman-original.svg"
}


ICON_CACHE = {}


def get_icon_svg(name):
    """
    Download a technology SVG and extract its inner SVG markup.

    The icon is embedded directly into the dashboard instead
    of relying on an external <img> request when the README
    is rendered.
    """

    if name in ICON_CACHE:
        return ICON_CACHE[name]

    url = ICON_URLS.get(name)

    if not url:
        return None

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Jitanka-GitHub-Profile"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:
            raw_svg = response.read().decode("utf-8")

        # Remove XML declaration if present.
        raw_svg = re.sub(
            r"<\?xml.*?\?>",
            "",
            raw_svg,
            flags=re.DOTALL
        )

        # Remove DOCTYPE if present.
        raw_svg = re.sub(
            r"<!DOCTYPE.*?>",
            "",
            raw_svg,
            flags=re.DOTALL
        )

        # Extract the contents of the root SVG element.
        match = re.search(
            r"<svg\b[^>]*>(.*?)</svg>",
            raw_svg,
            flags=re.DOTALL | re.IGNORECASE
        )

        if not match:
            print(f"Could not parse icon SVG for {name}")
            return None

        inner_svg = match.group(1).strip()

        ICON_CACHE[name] = inner_svg

        return inner_svg

    except Exception as error:
        print(
            f"Could not load icon for {name}: {error}"
        )
        return None


# ============================================================
# BASIC PROFILE
# ============================================================

print("Fetching GitHub profile...")

user = github_get(
    f"{API_URL}/users/{USERNAME}"
)

public_repositories = user["public_repos"]
followers = user["followers"]
following = user["following"]


# ============================================================
# REPOSITORIES
# ============================================================

print("Fetching repositories...")

repos = github_get(
    f"{API_URL}/users/{USERNAME}/repos"
    f"?per_page=100&type=owner&sort=updated"
)

# Only repositories owned by the user.
repos = [
    repo
    for repo in repos
    if not repo.get("fork", False)
]


# ============================================================
# TOTAL STARS
# ============================================================

total_stars = sum(
    repo.get("stargazers_count", 0)
    for repo in repos
)


# ============================================================
# LANGUAGE DISTRIBUTION
#
# GitHub's language endpoint returns byte counts for each
# language used in a repository.
# ============================================================

print("Fetching language statistics...")

language_bytes = defaultdict(int)

for repo in repos:

    owner = repo["owner"]["login"]
    name = repo["name"]

    try:

        languages = github_get(
            f"{API_URL}/repos/{owner}/{name}/languages"
        )

        for language, byte_count in languages.items():
            language_bytes[language] += byte_count

    except Exception as error:

        print(
            f"Could not read languages for {name}: {error}"
        )


sorted_languages = sorted(
    language_bytes.items(),
    key=lambda item: item[1],
    reverse=True
)

# Keep visualization compact.
top_languages = sorted_languages[:5]

other_bytes = sum(
    value
    for _, value in sorted_languages[5:]
)

if other_bytes > 0:
    top_languages.append(
        ("Others", other_bytes)
    )


language_total = sum(
    value
    for _, value in top_languages
)


# ============================================================
# CONTRIBUTION CALENDAR
#
# Fetch the last 365 days from GitHub GraphQL.
# ============================================================

print("Fetching contribution activity...")

now = datetime.now(timezone.utc)

from_date = (
    now - timedelta(days=365)
).strftime("%Y-%m-%dT00:00:00Z")

to_date = now.strftime(
    "%Y-%m-%dT23:59:59Z"
)


query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions

        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""


graphql_data = github_graphql(
    query,
    {
        "login": USERNAME,
        "from": from_date,
        "to": to_date
    }
)


calendar = (
    graphql_data["user"]
    ["contributionsCollection"]
    ["contributionCalendar"]
)


weeks = calendar["weeks"]

total_contributions = calendar[
    "totalContributions"
]


days = []

for week in weeks:
    for day in week["contributionDays"]:
        days.append(day)


# ============================================================
# CONTRIBUTION STREAK CALCULATIONS
# ============================================================

day_map = {
    day["date"]: day["contributionCount"]
    for day in days
}


sorted_dates = sorted(
    day_map.keys()
)


def calculate_streaks():

    if not sorted_dates:
        return 0, 0

    # --------------------------------------------------------
    # Current streak
    # --------------------------------------------------------

    current = 0

    today = datetime.now(
        timezone.utc
    ).date()

    cursor = today

    # If today has no contribution yet,
    # start from yesterday.
    if day_map.get(
        cursor.isoformat(),
        0
    ) == 0:

        cursor -= timedelta(days=1)

    while day_map.get(
        cursor.isoformat(),
        0
    ) > 0:

        current += 1

        cursor -= timedelta(days=1)


    # --------------------------------------------------------
    # Longest streak
    # --------------------------------------------------------

    longest = 0
    running = 0
    previous = None

    for date_string in sorted_dates:

        date_value = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()

        if day_map[date_string] > 0:

            if (
                previous is not None
                and date_value
                == previous + timedelta(days=1)
            ):

                running += 1

            else:

                running = 1

            longest = max(
                longest,
                running
            )

        else:

            running = 0

        previous = date_value

    return current, longest


current_streak, longest_streak = (
    calculate_streaks()
)


# ============================================================
# SVG HELPERS
# ============================================================

def esc(value):

    value = str(value)

    return (
        value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def text(
    x,
    y,
    content,
    size=14,
    weight="400",
    fill="#f0f6fc",
    anchor="start"
):

    return f"""
    <text
      x="{x}"
      y="{y}"
      font-family="Inter,Segoe UI,Arial,sans-serif"
      font-size="{size}px"
      font-weight="{weight}"
      fill="{fill}"
      text-anchor="{anchor}">
      {esc(content)}
    </text>
    """


def rect(
    x,
    y,
    width,
    height,
    fill="#0d1117",
    stroke="#30363d",
    radius=14
):

    return f"""
    <rect
      x="{x}"
      y="{y}"
      width="{width}"
      height="{height}"
      rx="{radius}"
      fill="{fill}"
      stroke="{stroke}"
      stroke-width="1"/>
    """


# ============================================================
# THEME
# ============================================================

BG = "#0d1117"
CARD = "#0d1117"
BORDER = "#30363d"

TEXT = "#f0f6fc"
MUTED = "#8b949e"

GREEN_1 = "#161b22"
GREEN_2 = "#0e4429"
GREEN_3 = "#006d32"
GREEN_4 = "#26a641"
GREEN_5 = "#39d353"


LANGUAGE_COLORS = [
    "#f1e05a",
    "#3178c6",
    "#3572A5",
    "#00B4AB",
    "#A97BFF",
    "#8b949e"
]


# ============================================================
# SVG DIMENSIONS
# ============================================================

WIDTH = 1200
HEIGHT = 1240

svg = []

svg.append(
    f"""
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="{WIDTH}"
      height="{HEIGHT}"
      viewBox="0 0 {WIDTH} {HEIGHT}">

      <rect
        width="{WIDTH}"
        height="{HEIGHT}"
        fill="{BG}"/>
    """
)


# ============================================================
# TECHNOLOGIES
# ============================================================

svg.append(
    text(
        600,
        44,
        "⚙  Technologies",
        27,
        "700",
        TEXT,
        "middle"
    )
)


svg.append(
    f"""
    <line
      x1="30"
      y1="65"
      x2="1170"
      y2="65"
      stroke="{BORDER}"/>

    <line
      x1="30"
      y1="96"
      x2="1170"
      y2="96"
      stroke="#484f58"
      stroke-width="5"/>
    """
)


# ============================================================
# LANGUAGE CARD
# ============================================================

svg.append(
    rect(
        30,
        112,
        550,
        260
    )
)


svg.append(
    text(
        54,
        145,
        "Languages used across my repositories",
        17,
        "700"
    )
)


# ============================================================
# DONUT CHART
# ============================================================

cx = 185
cy = 244

outer_radius = 82

svg.append(
    f"""
    <circle
      cx="{cx}"
      cy="{cy}"
      r="{outer_radius}"
      fill="none"
      stroke="#161b22"
      stroke-width="28"/>
    """
)


circumference = (
    2
    * 3.141592653589793
    * outer_radius
)

offset = 0


for index, (
    language,
    value
) in enumerate(top_languages):

    percentage = (
        value / language_total
        if language_total
        else 0
    )

    length = (
        circumference
        * percentage
    )

    color = LANGUAGE_COLORS[
        min(
            index,
            len(LANGUAGE_COLORS) - 1
        )
    ]

    svg.append(
        f"""
        <circle
          cx="{cx}"
          cy="{cy}"
          r="{outer_radius}"
          fill="none"
          stroke="{color}"
          stroke-width="28"
          stroke-dasharray="{length} {circumference - length}"
          stroke-dashoffset="{-offset}"
          transform="rotate(-90 {cx} {cy})"/>
        """
    )

    offset += length


svg.append(
    text(
        cx,
        cy - 3,
        "Top",
        14,
        "600",
        MUTED,
        "middle"
    )
)


svg.append(
    text(
        cx,
        cy + 18,
        "Languages",
        14,
        "600",
        MUTED,
        "middle"
    )
)


# ============================================================
# LANGUAGE LEGEND
# ============================================================

legend_y = 177


for index, (
    language,
    value
) in enumerate(top_languages):

    percentage = (
        value / language_total * 100
        if language_total
        else 0
    )

    color = LANGUAGE_COLORS[
        min(
            index,
            len(LANGUAGE_COLORS) - 1
        )
    ]

    y = (
        legend_y
        + index * 36
    )

    svg.append(
        f"""
        <circle
          cx="330"
          cy="{y - 5}"
          r="7"
          fill="{color}"/>
        """
    )

    svg.append(
        text(
            350,
            y,
            language,
            15,
            "500",
            TEXT
        )
    )

    svg.append(
        text(
            540,
            y,
            f"{percentage:.1f}%",
            15,
            "500",
            MUTED,
            "end"
        )
    )


# ============================================================
# TECHNOLOGIES & TOOLS CARD
# ============================================================

svg.append(
    rect(
        600,
        112,
        570,
        260
    )
)


svg.append(
    text(
        624,
        145,
        "Technologies & Tools",
        17,
        "700"
    )
)


# Your selected technology stack.
tools = [
    "Java",
    "Python",
    "C",
    "JavaScript",
    "React",
    "Flutter",
    "Node.js",
    "Express.js",
    "Firebase",
    "MySQL",
    "Git",
    "GitHub",
    "PyTorch",
    "OpenCV",
    "n8n",
    "Postman"
]


# ============================================================
# TECHNOLOGY ICON TILES
# ============================================================

tile_width = 54
tile_height = 54

start_x = 625
start_y = 180

horizontal_gap = 66
vertical_gap = 75


for index, tool in enumerate(tools):

    row = index // 8
    col = index % 8

    x = (
        start_x
        + col * horizontal_gap
    )

    y = (
        start_y
        + row * vertical_gap
    )


    # Tile
    svg.append(
        f"""
        <rect
          x="{x}"
          y="{y}"
          width="{tile_width}"
          height="{tile_height}"
          rx="12"
          fill="#161b22"
          stroke="{BORDER}"
          stroke-width="1"/>
        """
    )


    # Actual technology icon
    icon_svg = get_icon_svg(tool)


    if icon_svg:

        svg.append(
            f"""
            <g
              transform="
                translate({x + 11},{y + 11})
                scale(0.32)
              "
              width="100"
              height="100">

              {icon_svg}

            </g>
            """
        )

    else:

        # Fallback if an icon cannot be downloaded.
        fallback = {
            "Java": "☕",
            "Python": "PY",
            "C": "C",
            "JavaScript": "JS",
            "React": "⚛",
            "Flutter": "F",
            "Node.js": "JS",
            "Express.js": "EX",
            "Firebase": "FB",
            "MySQL": "SQL",
            "Git": "G",
            "GitHub": "GH",
            "PyTorch": "PT",
            "OpenCV": "CV",
            "n8n": "N8",
            "Postman": "PM"
        }.get(tool, tool[:2])

        svg.append(
            text(
                x + 27,
                y + 34,
                fallback,
                16,
                "700",
                TEXT,
                "middle"
            )
        )


# ============================================================
# STATISTICS
# ============================================================

svg.append(
    text(
        600,
        418,
        "⌁  Statistics",
        27,
        "700",
        TEXT,
        "middle"
    )
)


svg.append(
    f"""
    <line
      x1="30"
      y1="440"
      x2="1170"
      y2="440"
      stroke="{BORDER}"/>

    <line
      x1="30"
      y1="470"
      x2="1170"
      y2="470"
      stroke="#484f58"
      stroke-width="5"/>
    """
)


stats = [
    (
        "Repositories",
        public_repositories,
        "▣"
    ),
    (
        "Total Stars",
        total_stars,
        "★"
    ),
    (
        "Followers",
        followers,
        "●"
    ),
    (
        "Following",
        following,
        "●"
    )
]


card_width = 270
gap = 20


for index, (
    label,
    value,
    icon
) in enumerate(stats):

    x = (
        30
        + index * (card_width + gap)
    )


    svg.append(
        rect(
            x,
            490,
            card_width,
            105
        )
    )


    svg.append(
        f"""
        <rect
          x="{x + 18}"
          y="510"
          width="50"
          height="50"
          rx="12"
          fill="#161b22"
          stroke="{BORDER}"/>
        """
    )


    svg.append(
        text(
            x + 43,
            543,
            icon,
            21,
            "700",
            TEXT,
            "middle"
        )
    )


    svg.append(
        text(
            x + 82,
            538,
            str(value),
            26,
            "700"
        )
    )


    svg.append(
        text(
            x + 82,
            565,
            label,
            14,
            "500",
            MUTED
        )
    )


# ============================================================
# GITHUB ACTIVITY
# ============================================================

svg.append(
    text(
        600,
        640,
        "⌁  GitHub Activity",
        27,
        "700",
        TEXT,
        "middle"
    )
)


svg.append(
    f"""
    <line
      x1="30"
      y1="662"
      x2="1170"
      y2="662"
      stroke="{BORDER}"/>

    <line
      x1="30"
      y1="692"
      x2="1170"
      y2="692"
      stroke="#484f58"
      stroke-width="5"/>
    """
)


# ============================================================
# CONTRIBUTION CARD
# ============================================================

svg.append(
    rect(
        30,
        712,
        670,
        270
    )
)


svg.append(
    text(
        54,
        744,
        "Contribution Activity",
        17,
        "700"
    )
)


# ============================================================
# CONTRIBUTION GRID
#
# 53 weeks x 7 days.
# Sized to stay inside the 670px card.
# ============================================================

recent_weeks = weeks[-53:]


grid_x = 55
grid_y = 795

cell = 10
cell_gap = 2


levels = {
    "NONE": GREEN_1,
    "FIRST_QUARTILE": GREEN_2,
    "SECOND_QUARTILE": GREEN_3,
    "THIRD_QUARTILE": GREEN_4,
    "FOURTH_QUARTILE": GREEN_5
}


for week_index, week in enumerate(
    recent_weeks
):

    for day_index, day in enumerate(
        week["contributionDays"]
    ):

        x = (
            grid_x
            + week_index * (
                cell + cell_gap
            )
        )

        y = (
            grid_y
            + day_index * (
                cell + cell_gap
            )
        )


        level = day[
            "contributionLevel"
        ]


        fill = levels.get(
            level,
            GREEN_1
        )


        svg.append(
            f"""
            <rect
              x="{x}"
              y="{y}"
              width="{cell}"
              height="{cell}"
              rx="2"
              fill="{fill}"/>
            """
        )


# ============================================================
# MONTH LABELS
# ============================================================

month_positions = {}


for week_index, week in enumerate(
    recent_weeks
):

    for day in week["contributionDays"]:

        date = datetime.strptime(
            day["date"],
            "%Y-%m-%d"
        )


        if date.day <= 7:

            month = date.strftime(
                "%b"
            )

            month_positions.setdefault(
                month,
                week_index
            )


for month, week_index in (
    month_positions.items()
):

    x = (
        grid_x
        + week_index * (
            cell + cell_gap
        )
    )


    svg.append(
        text(
            x,
            775,
            month,
            11,
            "500",
            MUTED
        )
    )


# ============================================================
# CONTRIBUTION TOTAL
# ============================================================

svg.append(
    text(
        54,
        953,
        f"Total contributions: {total_contributions}",
        13,
        "500",
        MUTED
    )
)


# ============================================================
# STREAK CARD
# ============================================================

svg.append(
    rect(
        720,
        712,
        450,
        270
    )
)


svg.append(
    text(
        744,
        744,
        "Streak Stats",
        17,
        "700"
    )
)


streak_stats = [
    (
        "Current Streak",
        current_streak
    ),
    (
        "Longest Streak",
        longest_streak
    ),
    (
        "Contributions",
        total_contributions
    )
]


for index, (
    label,
    value
) in enumerate(streak_stats):

    x = (
        765
        + index * 142
    )


    svg.append(
        text(
            x,
            830,
            str(value),
            26,
            "700",
            TEXT,
            "middle"
        )
    )


    svg.append(
        text(
            x,
            858,
            label,
            12,
            "600",
            MUTED,
            "middle"
        )
    )


    svg.append(
        text(
            x,
            883,
            "Last year",
            11,
            "400",
            MUTED,
            "middle"
        )
    )


# ============================================================
# GITHUB PRESENCE
# ============================================================

svg.append(
    text(
        305,
        1030,
        "⌁  GitHub presence",
        22,
        "700",
        TEXT,
        "middle"
    )
)


svg.append(
    f"""
    <line
      x1="30"
      y1="1050"
      x2="580"
      y2="1050"
      stroke="{BORDER}"/>

    <line
      x1="30"
      y1="1070"
      x2="580"
      y2="1070"
      stroke="#484f58"
      stroke-width="4"/>
    """
)


presence = [
    (
        "Followers",
        followers
    ),
    (
        "Stars",
        total_stars
    ),
    (
        "Repositories",
        public_repositories
    )
]


for index, (
    label,
    value
) in enumerate(presence):

    x = (
        30
        + index * 180
    )


    svg.append(
        rect(
            x,
            1090,
            165,
            70
        )
    )


    svg.append(
        text(
            x + 18,
            1118,
            label,
            12,
            "500",
            MUTED
        )
    )


    svg.append(
        text(
            x + 18,
            1144,
            str(value),
            22,
            "700"
        )
    )


# ============================================================
# CONTACT
# ============================================================

svg.append(
    text(
        895,
        1030,
        "⌁  Contact",
        22,
        "700",
        TEXT,
        "middle"
    )
)


svg.append(
    f"""
    <line
      x1="620"
      y1="1050"
      x2="1170"
      y2="1050"
      stroke="{BORDER}"/>

    <line
      x1="620"
      y1="1070"
      x2="1170"
      y2="1070"
      stroke="#484f58"
      stroke-width="4"/>
    """
)


contacts = [
    (
        "Email",
        "mailto:jitankasarkar2017@gmail.com"
    ),
    (
        "LinkedIn",
        "https://linkedin.com/in/Jitankasarkar"
    ),
    (
        "GitHub",
        "https://github.com/Jitankasarkar"
    )
]


for index, (
    label,
    url
) in enumerate(contacts):

    x = (
        620
        + index * 183
    )


    svg.append(
        f"""
        <a href="{esc(url)}">

          <rect
            x="{x}"
            y="1090"
            width="165"
            height="70"
            rx="12"
            fill="{CARD}"
            stroke="{BORDER}"/>

          <text
            x="{x + 20}"
            y="1131"
            font-family="Inter,Segoe UI,Arial,sans-serif"
            font-size="13px"
            font-weight="600"
            fill="{TEXT}">
            {esc(label)}
          </text>

          <text
            x="{x + 145}"
            y="1132"
            font-family="Inter,Segoe UI,Arial,sans-serif"
            font-size="18px"
            fill="{MUTED}"
            text-anchor="middle">
            →
          </text>

        </a>
        """
    )


# ============================================================
# FOOTER
# ============================================================

generated_at = datetime.now(
    timezone.utc
).strftime(
    "%d %b %Y, %H:%M UTC"
)


svg.append(
    text(
        35,
        1210,
        f"Live GitHub data • Updated {generated_at}",
        11,
        "400",
        MUTED
    )
)


svg.append(
    text(
        600,
        1210,
        "⌘ Keep building. Keep learning.",
        13,
        "500",
        MUTED,
        "middle"
    )
)


# ============================================================
# CLOSE SVG
# ============================================================

svg.append(
    "</svg>"
)


# ============================================================
# WRITE DASHBOARD
# ============================================================

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)


OUTPUT.write_text(
    "".join(svg),
    encoding="utf-8"
)


print(
    f"Dashboard written to {OUTPUT}"
)

print()
print("Dashboard data:")
print(f"  Repositories: {public_repositories}")
print(f"  Stars:        {total_stars}")
print(f"  Followers:    {followers}")
print(f"  Following:    {following}")
print(f"  Contributions:{total_contributions}")
print(f"  Current streak: {current_streak}")
print(f"  Longest streak: {longest_streak}")
