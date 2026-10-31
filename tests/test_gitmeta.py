from guard import gitmeta


def test_github_actions_pull_request():
    env = {"GITHUB_ACTIONS": "true", "GUARD_GIT_SHA": "a1b2c3d4e5f6", "GUARD_PR": "4",
           "GITHUB_HEAD_REF": "cheaper-prompt", "GITHUB_REPOSITORY": "team/uncharted",
           "GITHUB_SHA": "mergecommit"}
    g = gitmeta.detect(env, use_git=False)
    assert g["sha"] == "a1b2c3d4e5f6" and g["short"] == "a1b2c3d"  # PR head, not merge commit
    assert g["pr"] == 4 and g["branch"] == "cheaper-prompt" and g["source"] == "github-actions"
    assert g["commit_url"] == "https://github.com/team/uncharted/commit/a1b2c3d4e5f6"
    assert g["pr_url"] == "https://github.com/team/uncharted/pull/4"


def test_render_deployment():
    env = {"RENDER_GIT_COMMIT": "ffff000011112222", "RENDER_GIT_BRANCH": "main",
           "RENDER_GIT_REPO_SLUG": "team/uncharted"}
    g = gitmeta.detect(env, use_git=False)
    assert g["source"] == "render" and g["branch"] == "main" and g["pr"] is None
    assert g["pr_url"] is None and g["commit_url"].endswith("/commit/ffff000011112222")


def test_nothing_known():
    assert gitmeta.detect({}, use_git=False) is None


def test_bad_pr_number_ignored():
    g = gitmeta.detect({"GUARD_GIT_SHA": "abc1234", "GUARD_PR": "four"}, use_git=False)
    assert g["pr"] is None and g["repo"] is None and g["commit_url"] is None


def test_local_git_does_not_crash():
    g = gitmeta.detect({})  # uses this checkout's git if available
    assert g is None or len(g["sha"]) >= 7


def test_parse_repo():
    assert gitmeta.parse_repo("https://github.com/rubella2121/uncharted.git") == "rubella2121/uncharted"
    assert gitmeta.parse_repo("git@github.com:rubella2121/uncharted.git") == "rubella2121/uncharted"
    assert gitmeta.parse_repo("http://proxy@127.0.0.1:1234/git/rubella2121/uncharted") == "rubella2121/uncharted"
    assert gitmeta.parse_repo(None) is None
