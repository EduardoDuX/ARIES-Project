"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or srcnstrate a feature.
"""

import asyncio
import json
import time
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import V20PresExRecord, V20PresExRecordList
from acapy_controller.protocols import (
    DIDResult,
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_anoncreds_publish_revocation,
    indy_anoncreds_revoke,
    indy_issue_credential_v2,
    indy_present_proof_v2,
    params,
)
from aiohttp import ClientSession

ALICE = getenv("ALICE", "http://eduardo:3001")
BOB = getenv("BOB", "http://bob:3001")


def summary(presentation: V20PresExRecord) -> str:
    """Summarize a presentation exchange record."""
    request = presentation.pres_request
    return "Summary: " + json.dumps(
        {
            "state": presentation.state,
            "verified": presentation.verified,
            "presentation_request": request.dict(by_alias=True) if request else None,
        },
        indent=2,
        sort_keys=True,
    )


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as eduardo, Controller(base_url=BOB) as bob:
        # Connecting
        eduardo_conn, bob_conn = await didexchange(eduardo, bob)

        # Issuance prep
        config = (await eduardo.get("/status/config"))["config"]
        genesis_url = config.get("ledger.genesis_url")
        public_did = (await eduardo.get("/wallet/did/public", response=DIDResult)).result
        if not public_did:
            public_did = (
                await eduardo.post(
                    "/wallet/did/create",
                    json={"method": "sov", "options": {"key_type": "ed25519"}},
                    response=DIDResult,
                )
            ).result
            assert public_did

            async with ClientSession() as session:
                register_url = genesis_url.replace("/genesis", "/register")
                async with session.post(
                    register_url,
                    json={
                        "did": public_did.did,
                        "verkey": public_did.verkey,
                        "alias": None,
                        "role": "ENDORSER",
                    },
                ) as resp:
                    assert resp.ok

            await eduardo.post("/wallet/did/public", params=params(did=public_did.did))
        schema, cred_def = await indy_anoncred_credential_artifacts(
            eduardo,
            ["firstname", "lastname"],
            support_revocation=True,
        )

        # Issue a credential
        eduardo_cred_ex, _ = await indy_issue_credential_v2(
            eduardo,
            bob,
            eduardo_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )
        issued_time = int(time.time())

        # Present the the credential's attributes
        await indy_present_proof_v2(
            bob,
            eduardo,
            bob_conn.connection_id,
            eduardo_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )

        # Revoke credential
        await indy_anoncreds_revoke(
            eduardo,
            cred_ex=eduardo_cred_ex,
            holder_connection_id=eduardo_conn.connection_id,
            notify=True,
        )
        await indy_anoncreds_publish_revocation(eduardo, cred_ex=eduardo_cred_ex)
        # TODO: Make this into a helper in protocols.py?
        await bob.record(topic="revocation-notification")
        revoked_time = int(time.time())

        # Request proof from holder again after revoking,
        # using the interval before cred revoked
        await indy_present_proof_v2(
            bob,
            eduardo,
            bob_conn.connection_id,
            eduardo_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [{"cred_def_id": cred_def.credential_definition_id}],
                }
            ],
            non_revoked={"from": issued_time, "to": issued_time},
        )

        # Request proof, no interval
        await indy_present_proof_v2(
            bob,
            eduardo,
            bob_conn.connection_id,
            eduardo_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [{"cred_def_id": cred_def.credential_definition_id}],
                }
            ],
        )

        # Request proof, using invalid/revoked interval but using
        # local non_revoked override (in requsted attrs)
        # ("LOCAL"-->requested attrs)
        await indy_present_proof_v2(
            bob,
            eduardo,
            bob_conn.connection_id,
            eduardo_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [{"cred_def_id": cred_def.credential_definition_id}],
                    "non_revoked": {
                        "from": issued_time,
                        "to": issued_time,
                    },
                }
            ],
            non_revoked={"from": revoked_time - 1, "to": revoked_time},
        )

        # Request proof, just local invalid interval
        await indy_present_proof_v2(
            bob,
            eduardo,
            bob_conn.connection_id,
            eduardo_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [{"cred_def_id": cred_def.credential_definition_id}],
                    "non_revoked": {
                        "from": revoked_time,
                        "to": revoked_time,
                    },
                }
            ],
        )

        # Query presentations
        presentations = await eduardo.get(
            "/present-proof-2.0/records",
            response=V20PresExRecordList,
        )

        # Presentation summary
        for i, pres in enumerate(presentations.results):
            print(summary(pres))


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
