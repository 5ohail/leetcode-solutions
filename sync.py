import json
import os
import re
import sys
import time
from pathlib import Path

import requests

GRAPHQL_URL = "https://leetcode.com/graphql/"
STATE_FILE = Path(".leetcode-sync-state.json")

SESSION_TOKEN = os.environ.get("LEETCODE_SESSION", "").strip()
CSRF_TOKEN = os.environ.get("LEETCODE_CSRF_TOKEN", "").strip()
USERNAME = os.environ.get("LEETCODE_USERNAME", "").strip()

LANGUAGE_EXTENSIONS = {
    "cpp": "cpp",
    "c++": "cpp",
    "c": "c",
    "python": "py",
    "python3": "py",
    "java": "java",
    "javascript": "js",
    "typescript": "ts",
    "csharp": "cs",
    "c#": "cs",
    "golang": "go",
    "go": "go",
    "rust": "rs",
    "kotlin": "kt",
    "swift": "swift",
    "ruby": "rb",
    "php": "php",
    "scala": "scala",
    "dart": "dart",
    "mysql": "sql",
    "mssql": "sql",
    "oraclesql": "sql",
    "postgresql": "sql",
    "pythonml": "py",
    "pythondata": "py",
}


def make_session():
    if not SESSION_TOKEN or not USERNAME:
        raise RuntimeError(
            "Missing LEETCODE_SESSION or LEETCODE_USERNAME "
            "in GitHub Secrets."
        )

    session = requests.Session()

    session.cookies.set(
        "LEETCODE_SESSION",
        SESSION_TOKEN,
        domain=".leetcode.com",
    )

    if CSRF_TOKEN:
        session.cookies.set(
            "csrftoken",
            CSRF_TOKEN,
            domain=".leetcode.com",
        )

    session.headers.update({
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com/",
        "User-Agent": "LeetCode-GitHub-Actions-Sync/1.0",
    })

    if CSRF_TOKEN:
        session.headers["x-csrftoken"] = CSRF_TOKEN

    return session


def graphql(session, query, variables):
    response = session.post(
        GRAPHQL_URL,
        json={
            "query": query,
            "variables": variables,
        },
        timeout=30,
    )

    response.raise_for_status()
    result = response.json()

    if result.get("errors"):
        messages = "; ".join(
            error.get("message", "Unknown GraphQL error")
            for error in result["errors"]
        )
        raise RuntimeError(f"LeetCode GraphQL error: {messages}")

    if "data" not in result or result["data"] is None:
        raise RuntimeError("LeetCode returned no GraphQL data.")

    return result["data"]


def load_state():
    if not STATE_FILE.exists():
        return {"processed_submission_ids": []}

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(
            f"Cannot read {STATE_FILE}: {exc}"
        ) from exc


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )


def get_recent_accepted_submissions(session):
    query = """
    query recentAccepted($username: String!) {
        recentAcSubmissionList(username: $username) {
            id
            title
            titleSlug
            timestamp
            statusDisplay
            lang
        }
    }
    """

    data = graphql(session, query, {"username": USERNAME})
    submissions = data.get("recentAcSubmissionList")

    if submissions is None:
        raise RuntimeError(
            "LeetCode did not return a submission list. "
            "Check your username and session credentials."
        )

    return [
        submission
        for submission in submissions
        if submission.get("statusDisplay", "").lower() == "accepted"
    ]


def get_submission_details(session, submission_id):
    query = """
    query submissionDetails($submissionId: Int!) {
        submissionDetails(submissionId: $submissionId) {
            code
            statusCode
            lang {
                name
                verboseName
            }
            question {
                title
                titleSlug
            }
        }
    }
    """

    data = graphql(
        session,
        query,
        {"submissionId": int(submission_id)},
    )

    details = data.get("submissionDetails")

    if not details:
        raise RuntimeError(
            f"Could not retrieve submission {submission_id}."
        )

    # LeetCode statusCode 10 represents an accepted submission.
    if details.get("statusCode") != 10:
        raise RuntimeError(
            f"Submission {submission_id} is no longer confirmed as accepted."
        )

    if not details.get("code"):
        raise RuntimeError(
            f"Submission {submission_id} returned no source code."
        )

    return details


def get_problem_number(session, title_slug):
    query = """
    query questionDetails($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
            questionFrontendId
            title
            titleSlug
        }
    }
    """

    data = graphql(
        session,
        query,
        {"titleSlug": title_slug},
    )

    question = data.get("question")

    if not question or not question.get("questionFrontendId"):
        raise RuntimeError(
            f"Could not find the problem number for {title_slug}."
        )

    return str(question["questionFrontendId"]), question["title"]


def safe_folder_name(text):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text.strip(".- ") or "Unknown-Problem"


def get_extension(language):
    normalized = language.strip().lower().replace(" ", "")

    extension = LANGUAGE_EXTENSIONS.get(normalized)

    if not extension:
        raise RuntimeError(
            f"Unsupported language '{language}'. "
            "Add its file extension to LANGUAGE_EXTENSIONS."
        )

    return extension


def write_solution(session, submission):
    submission_id = str(submission["id"])
    slug = submission["titleSlug"]

    details = get_submission_details(session, submission_id)

    # Use the language from the actual submitted code.
    language_info = details.get("lang") or {}
    language = (
        language_info.get("name")
        or submission.get("lang")
        or ""
    )

    extension = get_extension(language)

    problem_number, problem_title = get_problem_number(session, slug)

    folder = (
        f"{problem_number}-"
        f"{safe_folder_name(problem_title)}"
    )

    solution_path = Path(folder) / f"solution.{extension}"
    solution_path.parent.mkdir(parents=True, exist_ok=True)

    # Avoid replacing an existing solution for the same problem/language.
    # This preserves your original saved solution.
    if solution_path.exists():
        print(f"Already exists: {solution_path}")
        return

    solution_path.write_text(
        details["code"],
        encoding="utf-8",
    )

    print(f"Saved: {solution_path}")


def main():
    session = make_session()
    state = load_state()

    processed = {
        str(item)
        for item in state.get("processed_submission_ids", [])
    }

    submissions = get_recent_accepted_submissions(session)

    # Process older submissions first.
    submissions.sort(key=lambda item: int(item.get("timestamp", 0)))

    new_submissions = [
        submission
        for submission in submissions
        if str(submission["id"]) not in processed
    ]

    if not new_submissions:
        print("No new accepted submissions found.")
        return

    print(f"Found {len(new_submissions)} new accepted submission(s).")

    # Save state only after each submission has been processed successfully.
    for submission in new_submissions:
        submission_id = str(submission["id"])

        try:
            write_solution(session, submission)
        except Exception as exc:
            print(
                f"Failed to process submission {submission_id}: {exc}",
                file=sys.stderr,
            )
            raise

        processed.add(submission_id)

        state["processed_submission_ids"] = sorted(
            processed,
            key=lambda value: int(value),
        )
        save_state(state)

        # Keep requests modest to avoid unnecessary API traffic.
        time.sleep(1)

    print("LeetCode sync completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SYNC FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
