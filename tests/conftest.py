"""tests/conftest.py — Shared pytest fixtures for all test modules."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_rules_path() -> str:
    """Path to the sample rules YAML used in unit tests."""
    return "tests/fixtures/sample_rules.yaml"


@pytest.fixture
def valid_config() -> dict:
    """A config that passes all 8 policy rules."""
    return {
        "s3_bucket_public": False,
        "ssh_open_to_world": False,
        "rdp_open_to_world": False,
        "iam_wildcard": False,
        "instance_type": "t2.micro",
        "s3_encryption": True,
        "tags": {"Owner": "test", "Project": "aws-provisioner"},
        "cloudtrail_enabled": True,
    }


@pytest.fixture
def insecure_config() -> dict:
    """A config that triggers all block-level violations."""
    return {
        "s3_bucket_public": True,
        "ssh_open_to_world": True,
        "rdp_open_to_world": True,
        "iam_wildcard": True,
        "instance_type": "t2.micro",
        "s3_encryption": False,
        "tags": {},
        "cloudtrail_enabled": False,
    }
