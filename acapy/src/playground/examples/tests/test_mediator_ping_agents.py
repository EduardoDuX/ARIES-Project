"""Integration tests for Basic Message Storage."""

# pylint: disable=redefined-outer-name

import base64
import json as jsonlib
import os
import time
import uuid

import pytest

from . import ALICE, FABER, MULTI, Agent, logger

# add a blank line...
logger.info("start testing mediated connections...")


@pytest.fixture(scope="session")
def usp():
    """usp agent fixture."""
    logger.info(f"usp = {FABER}")
    yield Agent(FABER)


@pytest.fixture(scope="session")
def eduardo():
    """resolver agent fixture."""
    logger.info(f"eduardo = {ALICE}")
    yield Agent(ALICE)


@pytest.fixture(scope="session")
def multi_one():
    """resolver agent fixture."""
    agent = Agent(MULTI)
    wallet_name = f"multi_one_{str(uuid.uuid4())[0:8]}"
    resp = agent.create_tenant(wallet_name, "changeme")
    wallet_id = resp["wallet_id"]
    token = resp["token"]
    agent.headers = {"Authorization": f"Bearer {token}"}
    yield agent


@pytest.fixture(scope="session")
def mediation_invite():
    invitation_url = os.getenv("MEDIATOR_INVITATION_URL")
    logger.info(f"MEDIATOR_INVITATION_URL = {invitation_url}")
    base64_message = invitation_url.split("=", maxsplit=1)[1]
    base64_bytes = base64_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    data = message_bytes.decode("ascii")
    logger.info(f"invitation_block = {data}")
    yield data


def initialize_mediation(agent: Agent, invitation):
    connection_id = None
    mediator_connection_state = None
    mediation_id = None
    mediation_granted = False

    invitation_json = agent.receive_invite(
        invitation, auto_accept="true", alias="mediator"
    )
    connection_id = invitation_json["connection_id"]
    logger.info(f"connection_id: {connection_id}")
    time.sleep(2)

    attempts = 0
    while mediator_connection_state != "active" and attempts < 5:
        time.sleep(1)
        connection_json = agent.get_connection(connection_id)
        mediator_connection_state = connection_json["state"]
        logger.info(f"mediator_connection_state: {mediator_connection_state}")
        attempts = attempts + 1

    if mediator_connection_state == "active":
        mediation_request_json = agent.request_for_mediation(connection_id)
        mediation_id = mediation_request_json["mediation_id"]
        logger.info(f"mediation_id: {mediation_id}")
        mediation_granted = False
        attempts = 0
        while not mediation_granted and attempts < 5:
            time.sleep(1)
            granted_json = agent.get_mediation_request(mediation_id)
            mediation_granted = granted_json["state"] == "granted"
            logger.info(f"mediation_granted: {mediation_granted}")
            attempts = attempts + 1

    result = {
        "connection_id": connection_id,
        "mediation_id": mediation_id,
        "mediator_connection_state": mediator_connection_state,
        "mediation_granted": mediation_granted,
    }
    return result


@pytest.fixture(scope="session")
def usp_mediator(usp, mediation_invite):
    logger.info("usp_mediator...")
    result = initialize_mediation(usp, mediation_invite)
    logger.info(f"...usp_mediator = {result}")
    yield result


@pytest.fixture(scope="session")
def eduardo_mediator(eduardo, mediation_invite):
    logger.info("eduardo_mediator...")
    result = initialize_mediation(eduardo, mediation_invite)
    logger.info(f"...eduardo_mediator = {result}")
    yield result


@pytest.fixture(scope="session")
def multi_one_mediator(multi_one, mediation_invite):
    logger.info("multi_one_mediator...")
    result = initialize_mediation(multi_one, mediation_invite)
    logger.info(f"...multi_one_mediator = {result}")
    yield result


@pytest.mark.skipif(
    os.getenv("MEDIATOR_INVITATION_URL") in [None, "", " "],
    reason="MEDIATOR_INVITATION_URL not set. Running tests that do not require mediator.",
)
def test_mediated_single_tenants(
    usp, eduardo, usp_mediator, eduardo_mediator, mediation_invite
):
    assert usp_mediator["mediation_granted"] == True
    assert eduardo_mediator["mediation_granted"] == True

    resp = usp.create_invitation(
        alias="eduardo",
        auto_accept="true",
        json={"my_label": "usp", "mediation_id": usp_mediator["mediation_id"]},
    )
    usp_eduardo_connection_id = resp["connection_id"]
    logger.info(f"usp_eduardo_connection_id = {usp_eduardo_connection_id}")
    assert usp_eduardo_connection_id
    invite = resp["invitation"]
    logger.info(f"invite = {invite}")
    assert invite

    mediation_invite_json = jsonlib.loads(mediation_invite)
    logger.info(f"invitation service endpoint = {invite['serviceEndpoint']}")
    logger.info(f"mediator service endpoint = {mediation_invite_json['serviceEndpoint']}")
    assert invite["serviceEndpoint"] == mediation_invite_json["serviceEndpoint"]

    resp = eduardo.receive_invite(invite, alias="usp", auto_accept="true")
    eduardo_usp_connection_id = resp["connection_id"]
    logger.info(f"eduardo_usp_connection_id = {eduardo_usp_connection_id}")
    assert eduardo_usp_connection_id

    usp_eduardo_connection_active = False
    attempts = 0
    while not usp_eduardo_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = usp.get_connection(usp_eduardo_connection_id)
        usp_eduardo_connection_active = connection_resp["state"] == "active"
        logger.info(f"usp/eduardo active?  {usp_eduardo_connection_active}")
        attempts = attempts + 1

    eduardo_usp_connection_active = False
    attempts = 0
    while not eduardo_usp_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = eduardo.get_connection(eduardo_usp_connection_id)
        eduardo_usp_connection_active = connection_resp["state"] == "active"
        logger.info(f"eduardo/usp active?  {eduardo_usp_connection_active}")
        attempts = attempts + 1

    assert usp_eduardo_connection_active == True
    assert eduardo_usp_connection_active == True

    logger.info("usp eduardo pinging...")
    pings = 0
    while pings < 10:
        resp = usp.ping_connection(usp_eduardo_connection_id, "usp")
        logger.info(f"usp ping eduardo =  {resp}")
        time.sleep(1)
        eduardo.ping_connection(eduardo_usp_connection_id, "eduardo")
        logger.info(f"eduardo ping usp =  {resp}")
        time.sleep(1)
        pings = pings + 1


@pytest.mark.skipif(
    os.getenv("MEDIATOR_INVITATION_URL") in [None, "", " "],
    reason="MEDIATOR_INVITATION_URL not set. Running tests that do not require mediator.",
)
def test_mediated_multi_tenants(
    multi_one, eduardo, multi_one_mediator, eduardo_mediator, mediation_invite
):
    assert multi_one_mediator["mediation_granted"] == True
    assert eduardo_mediator["mediation_granted"] == True

    resp = multi_one.create_invitation(
        alias="eduardo",
        auto_accept="true",
        json={
            "my_label": "multi_one",
            "mediation_id": multi_one_mediator["mediation_id"],
        },
    )
    multi_one_eduardo_connection_id = resp["connection_id"]
    logger.info(f"multi_one_eduardo_connection_id = {multi_one_eduardo_connection_id}")
    assert multi_one_eduardo_connection_id
    invite = resp["invitation"]
    logger.info(f"invite = {invite}")
    assert invite

    mediation_invite_json = jsonlib.loads(mediation_invite)
    logger.info(f"invitation service endpoint = {invite['serviceEndpoint']}")
    logger.info(f"mediator service endpoint = {mediation_invite_json['serviceEndpoint']}")
    assert invite["serviceEndpoint"] == mediation_invite_json["serviceEndpoint"]

    resp = eduardo.receive_invite(invite, alias="multi_one", auto_accept="true")
    eduardo_multi_one_connection_id = resp["connection_id"]
    logger.info(f"eduardo_multi_one_connection_id = {eduardo_multi_one_connection_id}")
    assert eduardo_multi_one_connection_id

    multi_one_eduardo_connection_active = False
    attempts = 0
    while not multi_one_eduardo_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = multi_one.get_connection(multi_one_eduardo_connection_id)
        multi_one_eduardo_connection_active = connection_resp["state"] == "active"
        logger.info(f"multi_one/eduardo active?  {multi_one_eduardo_connection_active}")
        attempts = attempts + 1

    eduardo_multi_one_connection_active = False
    attempts = 0
    while not eduardo_multi_one_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = eduardo.get_connection(eduardo_multi_one_connection_id)
        eduardo_multi_one_connection_active = connection_resp["state"] == "active"
        logger.info(f"eduardo/multi_one active?  {eduardo_multi_one_connection_active}")
        attempts = attempts + 1

    assert multi_one_eduardo_connection_active == True
    assert eduardo_multi_one_connection_active == True

    logger.info("multi_one eduardo pinging...")
    pings = 0
    while pings < 10:
        resp = multi_one.ping_connection(multi_one_eduardo_connection_id, "multi_one")
        logger.info(f"multi_one ping eduardo =  {resp}")
        time.sleep(1)
        eduardo.ping_connection(eduardo_multi_one_connection_id, "eduardo")
        logger.info(f"eduardo ping multi_one =  {resp}")
        time.sleep(1)
        pings = pings + 1
