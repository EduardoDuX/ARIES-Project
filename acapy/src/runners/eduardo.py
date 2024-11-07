'''
Desenvolvido por Eduardo Zaffari Monteiro - NUSP: 12559490

Arquivo desenvolvido para a disciplina de Criptomoedas e Blockchain em 2024.2
'''


# Importando bibliotecas necessárias
import asyncio
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runners.agent_container import (
    AriesAgent,
    arg_parser,
    create_agent_with_args,
)
from runners.support.utils import (
    prompt,
    prompt_loop,
)

# Definindo o agente personalizado, herda da classe padrão AriesAgent
class EduardoAgent(AriesAgent):
    def __init__(
        self,
        ident: str,
        http_port: int,
        admin_port: int,
        no_auto: bool = False,
        aip: int = 20,
        endorser_role: str = None,
        log_file: str = None,
        log_config: str = None,
        log_level: str = None,
        **kwargs,
    ):
        super().__init__(
            ident,
            http_port,
            admin_port,
            prefix="Eduardo",
            no_auto=no_auto,
            seed=None,
            aip=aip,
            endorser_role=endorser_role,
            log_file=log_file,
            log_config=log_config,
            log_level=log_level,
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}

    # Método para detectar a conexão
    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    # Método que verifica o status da conexão
    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()


async def input_invitation(agent_container):
    '''
    Função conectar um agente em uma conversa
    
    Args:
        agent_container Agent: Agente que deve ser incluído em uma conversa
    '''
    # Verifica se a conexão está pronta
    agent_container.agent._connection_ready = asyncio.Future()

    # Recebe o convite e carrega os detalhes em formato JSON
    async for details in prompt_loop("Digite o convite para uma conversa: "):
        details = json.loads(details)
        break

    # Conecta o usuário à conversa
    connection = await agent_container.input_invitation(details, wait=True)


async def main(args):

    # Cria um agente
    eduardo_agent = await create_agent_with_args(
        args,
        ident="eduardo",
        extra_args=None,
    )

    # Instancia o agente personalizado
    agent = EduardoAgent(
        "eduardo.agent",
        eduardo_agent.start_port,
        eduardo_agent.start_port + 1,
        genesis_data=eduardo_agent.genesis_txns,
        genesis_txn_list=eduardo_agent.genesis_txn_list,
        no_auto=eduardo_agent.no_auto,
        tails_server_base_url=eduardo_agent.tails_server_base_url,
        revocation=eduardo_agent.revocation,
        timing=eduardo_agent.show_timing,
        multitenant=eduardo_agent.multitenant,
        mediation=eduardo_agent.mediation,
        wallet_type=eduardo_agent.wallet_type,
        aip=eduardo_agent.aip,
        endorser_role=eduardo_agent.endorser_role,
        log_file=eduardo_agent.log_file,
        log_config=eduardo_agent.log_config,
        log_level=eduardo_agent.log_level,
        reuse_connections=eduardo_agent.reuse_connections,
        extra_args=None,
    )

    # Inicializa o agente com o agente personalizado
    await eduardo_agent.initialize(the_agent=agent)

    # Requer um convite para uma conversa
    await input_invitation(eduardo_agent)

    # Opções a serem disponibilizadas ao usuário
    options = "    (1) Enviar mensagem\n    (X) Sair\n[1/X] "

    # Itera sobre as opções escolhidas
    async for option in prompt_loop(options):

        # Termina a execução
        if option == "X":
            await eduardo_agent.terminate()
            os._exit(1)

        # Envia uma mensagem ao usuário conectado
        elif option == "1":
            msg = await prompt("Digite sua mensagem: ")
            if msg:
                await eduardo_agent.agent.admin_POST(
                    f"/connections/{eduardo_agent.agent.connection_id}/send-message",
                    {"content": msg},
                )

if __name__ == "__main__":
    # Inicializa os argumentos passados
    parser = arg_parser(ident="eduardo", port=8030)
    args = parser.parse_args()

    # Executa o programa
    try:
        asyncio.get_event_loop().run_until_complete(main(args))
    except KeyboardInterrupt:
        os._exit(1)
