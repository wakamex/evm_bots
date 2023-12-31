"""Script for loading ETH & Elfpy agents with trading policies"""
from __future__ import annotations

import logging

import eth_utils
from numpy.random._generator import Generator as NumpyGenerator
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth
from elfpy.agents.agent import Agent
from elfpy.bots.bot_info import BotInfo
from elfpy.eth.accounts import EthAccount


def get_agent_accounts(
    config: list[BotInfo], web3: Web3, base_token_contract: Contract, hyperdrive_address: str, rng: NumpyGenerator
) -> list[EthAccount]:
    """Get agents according to provided config"""
    agents: list[EthAccount] = []
    num_agents_so_far: list[int] = []
    for agent_info in config:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        for policy_instance_index in range(agent_info.number_of_bots):
            kwargs["budget"] = agent_info.budget.sample_budget(rng)
            agent_count = policy_instance_index + sum(num_agents_so_far)
            # create agents
            policy = agent_info.policy(**kwargs)
            agent = Agent(wallet_address=agent_count, policy=policy)
            eth_account = eth.accounts.EthAccount(agent=agent, extra_entropy=str(agent_count))
            # fund test account with ether
            # TODO: raise issue on failure by looking at `rpc_response` returned from function
            _ = eth.set_anvil_account_balance(web3, eth_account.checksum_address, int(web3.to_wei(1000, "ether")))
            # fund test account by minting with the ERC20 base account
            # TODO: raise issue on failure by looking at `tx_receipt` returned from function
            _ = eth.smart_contract_transact(
                web3,
                base_token_contract,
                eth_account,
                "mint(address,uint256)",
                eth_account.checksum_address,
                kwargs["budget"].scaled_value,
            )
            # max approval for the hyperdrive contract
            # TODO: raise issue on failure by looking at `tx_receipt` returned from function
            _ = eth.smart_contract_transact(
                web3,
                base_token_contract,
                eth_account,
                "approve",
                hyperdrive_address,
                eth_utils.conversions.to_int(eth_utils.currency.MAX_WEI),
            )
            agents.append(eth_account)
        num_agents_so_far.append(agent_info.number_of_bots)
    logging.info("Added %d agents", sum(num_agents_so_far))
    return agents
