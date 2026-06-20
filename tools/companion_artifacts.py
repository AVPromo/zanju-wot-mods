"""Helpers for tracked companion-artifact metadata and local cache handling."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request

from .paths import REPO_ROOT, TOOLS_DIR

COMPANION_ARTIFACT_CACHE_DIR = os.path.join(REPO_ROOT, ".cache", "companion-wotmods")
COMPANION_ARTIFACT_MANIFEST_PATH = os.path.join(TOOLS_DIR, "companion_artifacts_manifest.json")
COMPANION_ARTIFACT_SCHEMA_VERSION = 1
RESEARCH_PROGRESS_BAR_BUNDLE = "research-progress-bar"
_DOWNLOAD_USER_AGENT = "zanju-wot-mods-tools/0.0.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CompanionArtifactError(RuntimeError):
    """Raised when companion-artifact metadata or cache state is invalid."""


def utc_now_iso():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_manifest(path=COMPANION_ARTIFACT_MANIFEST_PATH):
    if not os.path.isfile(path):
        raise CompanionArtifactError("Companion artifact manifest not found: {}".format(path))

    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    _validate_manifest(manifest, path)
    return manifest


def save_manifest(manifest, path=COMPANION_ARTIFACT_MANIFEST_PATH):
    _validate_manifest(manifest, path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=False)
        fh.write("\n")


def ensure_cache_dir(cache_dir=COMPANION_ARTIFACT_CACHE_DIR):
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": _DOWNLOAD_USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def download_url_to_path(url, destination_path):
    request = urllib.request.Request(url, headers={"User-Agent": _DOWNLOAD_USER_AGENT})
    parent = os.path.dirname(destination_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    try:
        with urllib.request.urlopen(request) as response, open(destination_path, "wb") as fh:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        return
    except urllib.error.HTTPError as exc:
        if exc.code != 403 or os.name != "nt":
            raise

    _download_url_with_powershell(url, destination_path)


def compute_file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def get_bundle_artifact_ids(manifest, bundle_name):
    bundles = manifest.get("bundles") or {}
    bundle = bundles.get(bundle_name)
    if not isinstance(bundle, dict):
        raise CompanionArtifactError("Bundle '{}' is not defined in the companion manifest".format(bundle_name))

    artifact_ids = bundle.get("artifactIds")
    if (
        not isinstance(artifact_ids, list)
        or not artifact_ids
        or not all(isinstance(item, str) for item in artifact_ids)
    ):
        raise CompanionArtifactError("Bundle '{}' must define a non-empty artifactIds list".format(bundle_name))
    return list(artifact_ids)


def manifest_defines_bundle(bundle_name, manifest=None):
    manifest = manifest or load_manifest()
    bundles = manifest.get("bundles") or {}
    return isinstance(bundles.get(bundle_name), dict)


def get_artifact_record(manifest, artifact_id):
    artifacts = manifest.get("artifacts") or {}
    artifact = artifacts.get(artifact_id)
    if not isinstance(artifact, dict):
        raise CompanionArtifactError("Artifact '{}' is not defined in the companion manifest".format(artifact_id))
    _validate_artifact_record(artifact_id, artifact)
    return artifact


def get_cached_artifact_path(cache_dir, artifact):
    filename = artifact.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        raise CompanionArtifactError("Artifact record is missing filename")
    return os.path.join(cache_dir, filename)


def fetch_manifest_artifacts(manifest=None, cache_dir=COMPANION_ARTIFACT_CACHE_DIR, artifact_ids=None, force=False):
    manifest = manifest or load_manifest()
    cache_dir = ensure_cache_dir(cache_dir)

    if artifact_ids is None:
        artifact_ids = sorted((manifest.get("artifacts") or {}).keys())
    if not artifact_ids:
        raise CompanionArtifactError("No companion artifacts are defined in the manifest")

    results = []
    for artifact_id in artifact_ids:
        artifact = get_artifact_record(manifest, artifact_id)
        path = get_cached_artifact_path(cache_dir, artifact)
        downloaded = force or not os.path.isfile(path)

        if not downloaded:
            try:
                verify_artifact_file(path, artifact)
            except CompanionArtifactError:
                downloaded = True

        if downloaded:
            _download_artifact_to_cache(path, artifact)

        results.append(
            {
                "artifactId": artifact_id,
                "artifact": artifact,
                "path": path,
                "downloaded": downloaded,
            }
        )

    return results


def resolve_cached_bundle_artifacts(bundle_name, manifest=None, cache_dir=COMPANION_ARTIFACT_CACHE_DIR):
    manifest = manifest or load_manifest()
    cache_dir = ensure_cache_dir(cache_dir)
    results = []
    for artifact_id in get_bundle_artifact_ids(manifest, bundle_name):
        artifact = get_artifact_record(manifest, artifact_id)
        path = get_cached_artifact_path(cache_dir, artifact)
        if not os.path.isfile(path):
            raise CompanionArtifactError(
                "Missing companion artifact '{}'; run zwm fetch-companion-artifacts first".format(
                    artifact.get("filename")
                )
            )
        verify_artifact_file(path, artifact)
        results.append({"artifactId": artifact_id, "artifact": artifact, "path": path})
    return results


def verify_artifact_file(path, artifact):
    expected_sha256 = _normalize_sha256(artifact.get("sha256"), artifact.get("filename", path))
    actual_sha256 = compute_file_sha256(path)
    if actual_sha256 != expected_sha256:
        raise CompanionArtifactError(
            "Checksum mismatch for {}: expected {}, got {}".format(path, expected_sha256, actual_sha256)
        )


def _download_artifact_to_cache(destination_path, artifact):
    cache_dir = os.path.dirname(destination_path)
    os.makedirs(cache_dir, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=os.path.basename(destination_path) + ".",
            suffix=".part",
            dir=cache_dir,
            delete=False,
        ) as fh:
            temp_path = fh.name

        download_url_to_path(artifact["downloadUrl"], temp_path)
        verify_artifact_file(temp_path, artifact)
        os.replace(temp_path, destination_path)
    finally:
        if temp_path and os.path.isfile(temp_path):
            os.remove(temp_path)


def _download_url_with_powershell(url, destination_path):
    escaped_url = url.replace("'", "''")
    escaped_destination_path = destination_path.replace("'", "''")
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "$ProgressPreference='SilentlyContinue'; "
            "Invoke-WebRequest -UseBasicParsing -Uri '{}' -OutFile '{}'".format(
                escaped_url,
                escaped_destination_path,
            )
        ),
    ]
    subprocess.check_call(command)


def _normalize_sha256(value, artifact_name):
    text = "{}".format(value or "").strip().lower()
    if not _SHA256_RE.match(text):
        raise CompanionArtifactError("Artifact '{}' has invalid sha256 metadata".format(artifact_name))
    return text


def _validate_manifest(manifest, source_name):
    if not isinstance(manifest, dict):
        raise CompanionArtifactError("Companion artifact manifest must be a JSON object: {}".format(source_name))

    schema_version = manifest.get("schemaVersion")
    if schema_version != COMPANION_ARTIFACT_SCHEMA_VERSION:
        raise CompanionArtifactError(
            "Unsupported companion artifact schemaVersion '{}' in {}".format(schema_version, source_name)
        )

    bundles = manifest.get("bundles")
    artifacts = manifest.get("artifacts")
    if not isinstance(bundles, dict) or not bundles:
        raise CompanionArtifactError("Companion artifact manifest must define bundles: {}".format(source_name))
    if not isinstance(artifacts, dict) or not artifacts:
        raise CompanionArtifactError("Companion artifact manifest must define artifacts: {}".format(source_name))

    for artifact_id, artifact in artifacts.items():
        if not isinstance(artifact_id, str) or not artifact_id:
            raise CompanionArtifactError("Companion artifact ids must be non-empty strings")
        _validate_artifact_record(artifact_id, artifact)

    for bundle_name, bundle in bundles.items():
        if not isinstance(bundle_name, str) or not bundle_name:
            raise CompanionArtifactError("Bundle names must be non-empty strings")
        if not isinstance(bundle, dict):
            raise CompanionArtifactError("Bundle '{}' must be an object".format(bundle_name))
        artifact_ids = bundle.get("artifactIds")
        if not isinstance(artifact_ids, list) or not artifact_ids:
            raise CompanionArtifactError("Bundle '{}' must define artifactIds".format(bundle_name))
        for artifact_id in artifact_ids:
            if artifact_id not in artifacts:
                raise CompanionArtifactError(
                    "Bundle '{}' references unknown artifact '{}'".format(bundle_name, artifact_id)
                )


def _validate_artifact_record(artifact_id, artifact):
    if not isinstance(artifact, dict):
        raise CompanionArtifactError("Artifact '{}' must be an object".format(artifact_id))
    for key in ("displayName", "provider", "project", "releaseTag", "version", "filename", "downloadUrl", "sha256"):
        value = artifact.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CompanionArtifactError("Artifact '{}' is missing '{}' metadata".format(artifact_id, key))
    _normalize_sha256(artifact.get("sha256"), artifact_id)
