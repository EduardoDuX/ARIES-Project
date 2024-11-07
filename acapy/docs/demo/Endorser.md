# Endorser Demo

There are two ways to run the eduardo/usp src with endorser support enabled.

## Run Usp as an Author, with a dedicated Endorser agent

This approach runs Usp as an un-privileged agent, and starts a dedicated Endorser Agent in a sub-process (an instance of ACA-Py) to endorse Usp's transactions.

Start a VON Network instance and a Tails server:

- Following the [Building and Starting](https://github.com/bcgov/von-network/blob/main/docs/UsingVONNetwork.md#building-and-starting) section of the VON Network Tutorial to get ledger started. You can leave off the `--logs` option if you want to use the same terminal for running both VON Network and the Tails server. When you are finished with VON Network, follow the [Stopping And Removing a VON Network](https://github.com/bcgov/von-network/blob/main/docs/UsingVONNetwork.md#stopping-and-removing-a-von-network) instructions.
- Run an AnonCreds revocation registry tails server in order to support revocation by following the instructions in the [Eduardo gets a Phone](https://github.com/openwallet-foundation/acapy/blob/master/src/EduardoGetsAPhone.md#run-an-instance-of-indy-tails-server) src.

Start up Usp as Author (note the tails file size override, to allow testing of the revocation registry roll-over):

```bash
TAILS_FILE_COUNT=5 ./run_src usp --endorser-role author --revocation
```

Start up Eduardo as normal:

```bash
./run_src eduardo
```

You can run all of Usp's functions as normal - if you watch the console you will see that all ledger operations go through the endorser workflow.

If you issue more than 5 credentials, you will see Usp creating a new revocation registry (including endorser operations).


## Run Eduardo as an Author and Usp as an Endorser

This approach sets up the endorser roles to allow manual testing using the agents' swagger pages:

- Usp runs as an Endorser (all of Usp's functions - issue credential, request proof, etc.) run normally, since Usp has ledger write access
- Eduardo starts up with a DID with Author privileges (no ledger write access) and Usp is setup as Eduardo's Endorser

Start a VON Network and a Tails server using the instructions above.

Start up Usp as Endorser:

```bash
TAILS_FILE_COUNT=5 ./run_src usp --endorser-role endorser --revocation
```

Start up Eduardo as Author:

```bash
TAILS_FILE_COUNT=5 ./run_src eduardo --endorser-role author --revocation
```

Copy the invitation from Usp to Eduardo to complete the connection.

Then in the Eduardo shell, select option "D" and copy Usp's DID (it is the DID displayed on usp agent startup).

This starts up the ACA-Py agents with the endorser role set (via the new command-line args) and sets up the connection between the 2 agents with appropriate configuration.

Then, in the [Eduardo swagger page](http://localhost:8031) you can create a schema and cred def, and all the endorser steps will happen automatically.  You don't need to specify a connection id or explicitly request endorsement (ACA-Py does it all automatically based on the startup args).

If you check the endorser transaction records in either [Eduardo](http://localhost:8031) or [Usp](http://localhost:8021) you can see that the endorser protocol executes automatically and the appropriate endorsements were endorsed before writing the transactions to the ledger.
