"""Integration tests for Basic Message Storage."""

# pylint: disable=redefined-outer-name

import os
import time
import uuid

import pytest

from . import ALICE, FABER, MULTI, Agent, logger


@pytest.fixture(scope="session")
def usp():
    """usp agent fixture."""
    yield Agent(FABER)


@pytest.fixture(scope="session")
def eduardo():
    """resolver agent fixture."""
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


@pytest.fixture(scope="session", autouse=True)
def eduardo_usp_connection(usp, eduardo):
    """Established connection filter."""
    logger.info("usp create invitation to eduardo")
    invite = usp.create_invitation(auto_accept="true")["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info("eduardo receive invitation")
    resp = eduardo.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"eduardo/usp connection_id = {result}")
    return result


@pytest.fixture(scope="session", autouse=True)
def usp_eduardo_connection(usp, eduardo):
    """Established connection filter."""
    logger.info("eduardo create invitation to usp")
    invite = eduardo.create_invitation(auto_accept="true")["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info("usp receive invitation")
    resp = usp.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"usp/eduardo connection_id = {result}")
    return result


@pytest.fixture(scope="session", autouse=True)
def eduardo_multi_one_connection(multi_one, eduardo):
    """Established connection filter."""
    logger.info("multi_one create invitation to eduardo")
    invite = multi_one.create_invitation(auto_accept="true")["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info("eduardo receive invitation")
    resp = eduardo.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"eduardo/multi_one connection_id = {result}")
    return result


@pytest.fixture(scope="session", autouse=True)
def multi_one_eduardo_connection(multi_one, eduardo):
    """Established connection filter."""
    logger.info("eduardo create invitation to multi_one")
    invite = eduardo.create_invitation(auto_accept="true")["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info("usp receive invitation")
    resp = multi_one.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"multi_one/eduardo connection_id = {result}")
    return result


@pytest.mark.skipif(
    os.getenv("MEDIATOR_INVITATION_URL") not in [None, "", " "],
    reason="MEDIATOR_INVITATION_URL is set. Running only tests that require mediator.",
)
def test_single_tenants(usp, eduardo, usp_eduardo_connection, eduardo_usp_connection):
    usp_eduardo_connection_active = False
    attempts = 0
    while not usp_eduardo_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = usp.get_connection(usp_eduardo_connection)
        usp_eduardo_connection_active = connection_resp["state"] == "active"
        logger.info(f"usp/eduardo active?  {usp_eduardo_connection_active}")
        attempts = attempts + 1

    eduardo_usp_connection_active = False
    attempts = 0
    while not eduardo_usp_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = eduardo.get_connection(eduardo_usp_connection)
        eduardo_usp_connection_active = connection_resp["state"] == "active"
        logger.info(f"eduardo/usp active?  {eduardo_usp_connection_active}")
        attempts = attempts + 1

    assert usp_eduardo_connection_active == True
    assert eduardo_usp_connection_active == True

    logger.info("usp eduardo pinging...")
    pings = 0
    while pings < 10:
        resp = usp.ping_connection(usp_eduardo_connection, "usp")
        logger.info(f"usp ping eduardo =  {resp}")
        time.sleep(1)
        eduardo.ping_connection(eduardo_usp_connection, "eduardo")
        logger.info(f"eduardo ping usp =  {resp}")
        time.sleep(1)
        pings = pings + 1


@pytest.mark.skipif(
    os.getenv("MEDIATOR_INVITATION_URL") not in [None, "", " "],
    reason="MEDIATOR_INVITATION_URL is set. Running only tests that require mediator.",
)
def test_multi_tenants(
    multi_one, eduardo, multi_one_eduardo_connection, eduardo_multi_one_connection
):
    multi_one_eduardo_connection_active = False
    attempts = 0
    while not multi_one_eduardo_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = multi_one.get_connection(multi_one_eduardo_connection)
        multi_one_eduardo_connection_active = connection_resp["state"] == "active"
        logger.info(f"multi_one/eduardo active?  {multi_one_eduardo_connection_active}")
        attempts = attempts + 1

    eduardo_multi_one_connection_active = False
    attempts = 0
    while not eduardo_multi_one_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = eduardo.get_connection(eduardo_multi_one_connection)
        eduardo_multi_one_connection_active = connection_resp["state"] == "active"
        logger.info(f"eduardo/multi_one active?  {eduardo_multi_one_connection_active}")
        attempts = attempts + 1

    assert multi_one_eduardo_connection_active == True
    assert eduardo_multi_one_connection_active == True

    logger.info("multi_one eduardo pinging...")
    pings = 0
    while pings < 10:
        resp = multi_one.ping_connection(multi_one_eduardo_connection, "multi_one")
        logger.info(f"multi_one ping eduardo =  {resp}")
        time.sleep(1)
        eduardo.ping_connection(eduardo_multi_one_connection, "eduardo")
        logger.info(f"eduardo ping multi_one =  {resp}")
        time.sleep(1)
        pings = pings + 1
