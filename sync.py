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

# Number of recent submissions to request.
SUBMISSION_LIMIT = 50

# Set to True to replace existing solutions with newly accepted code.
OVERWRITE_EXISTING_SOLUTIONS = False

LANGUAGE_EXTENSIONS = {
    "cpp": "cpp",
    "c++": "cpp",
    "c": "c",
    "python": "py",
    "python3": "py",
    "pythonml": "py",
    "pythondata": "py",
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
}


def make_session():
    if not SESSION_TOKEN or not USERNAME:
        raise RuntimeError(
            "Missing LEETCODE_SESSION or LEETCODE_USERNAME. "
            "Configure these in GitHub Actions Secrets."
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
        session.headers["x-csrftoken"] = CSRF_TOKEN

    session.headers.update({
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com/",
        "Origin": "https://leetcode.com",
        "User-Agent": "LeetCode-GitHub-Actions-Sync/2.0",
    })

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

    if response.status_code in (401, 403):
        raise RuntimeError(
            "LeetCode rejected the request. "
            "Your session cookie may have expired."
        )

    response.raise_for_status()

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "LeetCode returned an invalid JSON response."
        ) from exc

    if result.get("errors"):
        messages = "; ".join(
            error.get("message", "Unknown GraphQL error")
            for error in result["errors"]
        )
        raise RuntimeError(f"LeetCode GraphQL error: {messages}")

    if result.get("data") is None:
        raise RuntimeError("LeetCode returned no GraphQL data.")

    return result["data"]


def load_state():
    if not STATE_FILE.exists():
        return {"processed_submission_ids": []}

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

        if not isinstance(state, dict):
            raise ValueError("State must be a JSON object.")

        state.setdefault("processed_submission_ids", [])

        return state

    except (json.JSONDecodeError, OSError, ValueError) as exc:
        raise RuntimeError(
            f"Could not read {STATE_FILE}: {exc}"
        ) from exc


def save_state(state):
    temporary_file = STATE_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )

    temporary_file.replace(STATE_FILE)


def get_recent_accepted_submissions(session):
    query = """
    query recentAccepted($username: String!, $limit: Int) {
        recentAcSubmissionList(username: $username, limit: $limit) {
            id
            title
            titleSlug
            timestamp
            statusDisplay
            lang
        }
    }
    """

    data = graphql(
        session,
        query,
        {
            "username": USERNAME,
            "limit": SUBMISSION_LIMIT,
        },
    )

    submissions = data.get("recentAcSubmissionList")

    if submissions is None:
        raise RuntimeError(
            "LeetCode returned no submission list. "
            "Verify your username and session."
        )

    print(f"Retrieved {len(submissions)} recent submissions.")

    accepted = [
        submission
        for submission in submissions
        if submission.get("statusDisplay", "").lower() == "accepted"
    ]

    print(f"Accepted submissions found: {len(accepted)}")

    return accepted


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

    if details.get("statusCode") != 10:
        raise RuntimeError(
            f"Submission {submission_id} is not confirmed accepted."
        )

    code = details.get("code")

    if not isinstance(code, str) or not code.strip():
        raise RuntimeError(
            f"Submission {submission_id} contains no source code."
        )

    return details


def get_problem_details(session, title_slug):
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

    return (
        str(question["questionFrontendId"]),
        question.get("title") or title_slug,
    )


def safe_folder_name(text):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)

    return text.strip(".- ") or "Unknown-Problem"


def get_extension(language):
    normalized = language.strip().lower()
    normalized = normalized.replace(" ", "")

    extension = LANGUAGE_EXTENSIONS.get(normalized)

    if not extension:
        raise RuntimeError(
            f"Unsupported language: {language!r}. "
            "Add its extension to LANGUAGE_EXTENSIONS."
        )

    return extension


def write_solution(session, submission):
    submission_id = str(submission["id"])
    slug = submission["titleSlug"]

    details = get_submission_details(session, submission_id)

    language_info = details.get("lang") or {}

    language = (
        language_info.get("name")
        or submission.get("lang")
        or ""
    )

    extension = get_extension(language)

    problem_number, problem_title = get_problem_details(
        session,
        slug,
    )

    folder_name = (
        f"{problem_number}-"
        f"{safe_folder_name(problem_title)}"
    )

    folder = Path(folder_name)
    folder.mkdir(parents=True, exist_ok=True)

    solution_path = folder / f"solution.{extension}"

    code = details["code"]

    if solution_path.exists() and not OVERWRITE_EXISTING_SOLUTIONS:
        existing_code = solution_path.read_text(encoding="utf-8")

        if existing_code == code:
            print(f"Unchanged solution: {solution_path}")
            return False

        print(
            f"Existing solution preserved: {solution_path}. "
            "Enable OVERWRITE_EXISTING_SOLUTIONS to replace it."
        )
        return False

    if solution_path.exists():
        existing_code = solution_path.read_text(encoding="utf-8")

        if existing_code == code:
            print(f"Unchanged solution: {solution_path}")
            return False

    solution_path.write_text(code, encoding="utf-8")

    print(f"Saved solution: {solution_path}")

    return True


def main():
    session = make_session()
    state = load_state()

    processed = {
        str(item)
        for item in state.get("processed_submission_ids", [])
    }

    submissions = get_recent_accepted_submissions(session)

    submissions.sort(
        key=lambda item: int(item.get("timestamp", 0))
    )

    new_submissions = [
        submission
        for submission in submissions
        if str(submission["id"]) not in processed
    ]

    if not new_submissions:
        print(
            "No unprocessed accepted submissions found "
            "in the recent submission list."
        )
        return

    print(
        f"New submissions to process: {len(new_submissions)}"
    )

    saved_count = 0
    skipped_count = 0

    for submission in new_submissions:
        submission_id = str(submission["id"])

        try:
            saved = write_solution(session, submission)

            if saved:
                saved_count += 1
            else:
                skipped_count += 1

            # Mark processed only after handling the submission.
            processed.add(submission_id)

            state["processed_submission_ids"] = sorted(
                processed,
                key=lambda value: int(value),
            )

            save_state(state)

        except Exception as exc:
            print(
                f"Failed submission {submission_id}: {exc}",
                file=sys.stderr,
            )
            raise

        time.sleep(1)

    print("\n========== SYNC SUMMARY ==========")
    print(f"Processed submissions: {len(new_submissions)}")
    print(f"New or updated solution files: {saved_count}")
    print(f"Skipped existing solution files: {skipped_count}")
    print("==================================")
    print("LeetCode sync completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SYNC FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
