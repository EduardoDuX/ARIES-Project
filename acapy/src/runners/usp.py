'''
Desenvolvido por Eduardo Zaffari Monteiro - NUSP: 12559490

Arquivo desenvolvido para a disciplina de Criptomoedas e Blockchain em 2024.2
'''


# Importando bibliotecas necessárias
import asyncio
import datetime
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runners.agent_container import (
    AriesAgent,
    arg_parser,
    create_agent_with_args,
)

from runners.support.utils import prompt, prompt_loop

# Define o agente personalizado
class UspAgent(AriesAgent):
    def __init__(
        self,
        ident: str,
        http_port: int,
        admin_port: int,
        no_auto: bool = False,
        endorser_role: str = None,
        revocation: bool = False,
        anoncreds_legacy_revocation: str = None,
        log_file: str = None,
        log_config: str = None,
        log_level: str = None,
        **kwargs,
    ):
        super().__init__(
            ident,
            http_port,
            admin_port,
            prefix="Usp",
            no_auto=no_auto,
            endorser_role=endorser_role,
            revocation=revocation,
            anoncreds_legacy_revocation=anoncreds_legacy_revocation,
            log_file=log_file,
            log_config=log_config,
            log_level=log_level,
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}
        self.cred_attrs = {}

    # Método para detectar uma conexão
    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    # Método para verificar o status da conexão
    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

    def generate_credential_offer(self, cred_def_id):
        '''
        Função para gerar uma requisição de criação de credencial
        Args:
            cred_def_id: id para definição da credencial
        '''

        # Informações a serem adicionadas na credencial
        age = 21
        d = datetime.date.today()
        birth_date = datetime.date(d.year - age, d.month, d.day)
        birth_date_format = "%Y%m%d"
        
        self.cred_attrs[cred_def_id] = {
            "name": "Eduardo Zaffari",
            "date": "2024-11-12",
            "degree": "Ciência de Dados",
            "birthdate_dateint": birth_date.strftime(birth_date_format),
            "timestamp": str(int(time.time())),
        }

        # Tipo de credencial a ser utilizada
        cred_preview = {
            "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
            "attributes": [
                {"name": n, "value": v}
                for (n, v) in self.cred_attrs[cred_def_id].items()
            ],
        }

        # Conteúdo da requisição
        offer_request = {
            "connection_id": self.connection_id,
            "comment": f"Offer on cred def id {cred_def_id}",
            "auto_remove": False,
            "credential_preview": cred_preview,
            "filter": {"indy": {"cred_def_id": cred_def_id}},
            "trace": False,
        }
        return offer_request


    def generate_proof_request_web_request(self):
        '''
        Função que gera uma requisição de prova de identidade
        '''
    
        # Informações a serem utilizadas na prova
        age = 21
        d = datetime.date.today()
        birth_date = datetime.date(d.year - age, d.month, d.day)
        birth_date_format = "%Y%m%d"

        # Atributos a serem requisitados na prova
        req_attrs = [
            {
                "name": "name",
                "restrictions": [{"schema_name": "degree schema"}],
            },
            {
                "name": "date",
                "restrictions": [{"schema_name": "degree schema"}],
            },
            {
                "name": "degree",
                "restrictions": [{"schema_name": "degree schema"}],
            }
        ]

        # Predicado a ser provado, requer que a data de nascimento do usuário
        # seja menor que a data especificada para prova, para configurar uma 
        # Zero Knowledge Proof
        req_preds = [
            {
                "name": "birthdate_dateint",
                "p_type": "<=",
                "p_value": int(birth_date.strftime(birth_date_format)),
                "restrictions": [{"schema_name": "degree schema"}],
            }
        ]

        # Configurações da prova para a rede Indy
        indy_proof_request = {
            "name": "Proof of Education",
            "version": "1.0",
            "requested_attributes": {
                f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
            },
            "requested_predicates": {
                f"0_{req_pred['name']}_GE_uuid": req_pred
                for req_pred in req_preds
            },
        }

        # Conteúdo final da requisição
        proof_request_web_request = {
            "presentation_request": {"indy": indy_proof_request},
            "trace": False,
            "connection_id": self.connection_id
        }

        return proof_request_web_request


async def main(args):

    # Cria um agente
    usp_agent = await create_agent_with_args(
        args,
        ident="usp",
        extra_args=None,
    )

    # Instancia o agente personalizado
    agent = UspAgent(
        "usp.agent",
        usp_agent.start_port,
        usp_agent.start_port + 1,
        genesis_data=usp_agent.genesis_txns,
        genesis_txn_list=usp_agent.genesis_txn_list,
        no_auto=usp_agent.no_auto,
        tails_server_base_url=usp_agent.tails_server_base_url,
        revocation=usp_agent.revocation,
        timing=usp_agent.show_timing,
        multitenant=usp_agent.multitenant,
        mediation=usp_agent.mediation,
        wallet_type=usp_agent.wallet_type,
        seed=usp_agent.seed,
        aip=usp_agent.aip,
        endorser_role=usp_agent.endorser_role,
        anoncreds_legacy_revocation=usp_agent.anoncreds_legacy_revocation,
        log_file=usp_agent.log_file,
        log_config=usp_agent.log_config,
        log_level=usp_agent.log_level,
        reuse_connections=usp_agent.reuse_connections,
        multi_use_invitations=usp_agent.multi_use_invitations,
        public_did_connections=usp_agent.public_did_connections,
        extra_args=None,
    )

    # Especifica o schema de credencial a ser utilizado
    usp_schema_name = "degree schema"
    usp_schema_attrs = [
        "name",
        "date",
        "degree",
        "birthdate_dateint",
        "timestamp",
    ]
    
    # Configura que a identidade distribuída será pública
    usp_agent.public_did = True

    # Inicializa o agente
    await usp_agent.initialize(
        the_agent=agent,
        schema_name=usp_schema_name,
        schema_attrs=usp_schema_attrs,
        create_endorser_agent=False,
    )
    
    # Gera um convite para conversa
    await usp_agent.generate_invitation(
        display_qr=False,
        reuse_connections=usp_agent.reuse_connections,
        multi_use_invitations=usp_agent.multi_use_invitations,
        public_did_connections=usp_agent.public_did_connections,
        wait=True,
    )

    # Opções a serem mostradas ao usuário
    options = (
        "    (1) Enviar credencial ao usuário conectado\n"
        "    (2) Requisitar prova de identidade ao usuário conectado\n"
        "    (3) Enviar Mensagem\n"
        "    (X) Sair\n[1/2/3/X] "
    )

    # Itera sobre as opções
    async for option in prompt_loop(options):

        # Sai da aplicação
        if option == "X":
            await usp_agent.terminate()
            os._exit(1)

        # Faz uma requisição para criar identidade para o usuário conectado
        elif option == "1":
            offer_request = usp_agent.agent.generate_credential_offer(usp_agent.cred_def_id)

            await usp_agent.agent.admin_POST(
                "/issue-credential-2.0/send-offer", offer_request
            )

        # Faz uma requisição para validar a identidade do usuário conectado
        elif option == "2":
            proof_request_web_request = usp_agent.agent.generate_proof_request_web_request()

            await agent.admin_POST(
                "/present-proof-2.0/send-request", proof_request_web_request
            )

        # Envia uma mensagem ao usuário conectado
        elif option == "3":
            msg = await prompt("Digite sua mensagem: ")
            await usp_agent.agent.admin_POST(
                f"/connections/{usp_agent.agent.connection_id}/send-message",
                {"content": msg},
            )


if __name__ == "__main__":

    # Inicializa os argumentos passados
    parser = arg_parser(ident="usp", port=8020)
    args = parser.parse_args()

    # Executa o programa
    try:
        asyncio.get_event_loop().run_until_complete(main(args))
    except KeyboardInterrupt:
        os._exit(1)
