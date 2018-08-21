#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <nlpbox.programming@arne.cl>

import base64
import io
import os

import pexpect
import pytest
import requests
import sh
from PIL import Image
import imagehash


TEMP_PROJECT = '_temp_convert' # TODO: import it once we have a setup.py

TESTDIR = os.path.dirname(__file__)
RS3_FILEPATH = os.path.join(TESTDIR, 'test.rs3')
EXPECTED_PNG1 = os.path.join(TESTDIR, 'result1.png')
BASEURL = "http://127.0.0.1:8080/api"


@pytest.fixture(scope="session", autouse=True)
def start_api():
    """This function will start rstWeb in a separate process before the tests are
    run and shut it down afterwards.
    """
    print("starting rstWeb...")
    child = pexpect.spawn('python start_local.py')

    child.expect('Serving on http://127.0.0.1:8080')

    # delete all existing projects and documents before we start testing
    res = requests.delete('{}/projects'.format(BASEURL))
    assert res.status_code == 200

    # 'yield' provides the fixture value (we don't need it, but it marks the
    # point when the 'setup' part of this fixture ends).
    yield res

    print("stopping rstWeb...")
    child.close()


@pytest.fixture(scope="function", autouse=True)
def delete_projects():
    """delete all projects after each test function is finished"""
    # 'yield' provides the fixture value (we don't need it, but it marks the
    # point when the 'setup' part of this fixture ends).
    yield True

    # delete all existing projects and documents before we start testing
    res = requests.delete('{}/projects'.format(BASEURL))
    assert res.status_code == 200


def image_matches(produced_file, expected_files=[EXPECTED_PNG1]):
    """Return True, iff the average hash of the produced image matches any of the
    expected images.
    """
    produced_hash = imagehash.average_hash(Image.open(produced_file))

    expected_hashes = [imagehash.average_hash(Image.open(ef)) for ef in expected_files]
    return any([produced_hash == expected_hash for expected_hash in expected_hashes])


def get_projects():
    """GET /projects helper function"""
    res = requests.get('{}/projects'.format(BASEURL))
    return res.json()


def delete_project(project_name):
    res = requests.delete('{0}/projects/{1}'.format(BASEURL, project_name))
    assert res.status_code == 200


def add_project(project_name):
    res = requests.post('{0}/projects/{1}'.format(BASEURL, project_name))
    assert res.status_code == 200


def test_rs3_to_png():
    """The rstviewer-service API converts an .rs3 file into the expected image."""
    with open(RS3_FILEPATH) as input_file:
        input_text = input_file.read()

    res = requests.post(
        '{}/convert?input_format=rs3&output_format=png'.format(BASEURL),
        files={'input_file': input_text})
    # delete the project used for conversion
    delete_project(TEMP_PROJECT)

    assert image_matches(io.BytesIO(res.content))


def test_rs3_to_png_base64():
    """The rstviewer-service API converts an .rs3 file into the expected base64 encoded image."""
    with open(RS3_FILEPATH) as input_file:
        input_text = input_file.read()

    res = requests.post(
        '{}/convert?input_format=rs3&output_format=png-base64'.format(BASEURL),
        files={'input_file': input_text})
    png_bytes = base64.b64decode(res.content)
    # delete the project used for conversion
    delete_project(TEMP_PROJECT)

    assert image_matches(io.BytesIO(png_bytes))


def test_get_index():
    res = requests.get(BASEURL)
    assert 'rstWeb API' in res.content


def test_projects():
    """Projects can be added, removed and listed."""
    projects = get_projects()
    assert projects == []

    add_project("proj1")
    projects = get_projects()
    assert projects == ["proj1"]

    add_project("proj2")
    projects = get_projects()
    assert projects == ["proj1", "proj2"]

    delete_project("proj1")
    projects = get_projects()
    assert projects == ["proj2"]

    # delete all projects
    res = requests.delete('{}/projects'.format(BASEURL))
    assert res.status_code == 200
    projects = get_projects()
    assert projects == []

    # deleting a non-existing project should do nothing
    delete_project("nonexisting_project")
    projects = get_projects()
    assert projects == []
