from brownie import interface, accounts
from helpers.utils import connect_account
from helpers.addresses import r
import click
import brownie

REGISTRY = interface.IBadgerRegistryV2(r.registry_v2)
GUARDIAN = interface.IWarRoomGatedProxy(REGISTRY.get("guardian"))
YEARN_VAULT = r.yearn_vaults.byvWBTC

VAULT_STATUS = [0, 1, 2, 3]

def main():
    # Get caller account
    dev = connect_account()

    # Prompt if we should pause all (Should we not always do pause all here? Individual pauses are likely more efficient through etherscan)
    pause_all = click.prompt("Pause all?", type=click.Choice(["y", "n"]))

    # 1. If pause all, pause GAC (Doing it first as it will quickly pause most of the vaults), else, continue
    if pause_all == "y":
        GUARDIAN.pause(REGISTRY.get("globalAccessControl"), {"from": dev})

    # 2. Fetch all vaults from the Registry (V1, V1.5) for all status (deprecated, exp, guarded, open)
    print("Fetching vaults and strategies from Registry...")
    vaults_v1 = []
    for status in VAULT_STATUS:
        vaults_v1 += Extract(REGISTRY.getFilteredProductionVaults("v1", status))

    vaults_v1_5 = []
    for status in VAULT_STATUS:
        vaults_v1_5 += Extract(REGISTRY.getFilteredProductionVaults("v1.5", status))

    # 3. Fetch all strategies from the vaults and identify the vaults that can't be paused via GAC
    vaults_non_gac = []
    strategies = []
    # for i in range(len(vaults_v1)):
    for address in vaults_v1:
        vault = interface.ISettV4h(address)
        # Yearn vault doesn't contain controller/strategy
        if address != YEARN_VAULT:
            controller = interface.IController(vault.controller())
            strategies.append(controller.strategies(vault.token()))
            # Check if GAC variable exists on vault
            try:
                vault.GAC()
            except:
                vaults_non_gac.append(address)
        else:
            vaults_non_gac.append(address)

    for address in vaults_v1_5:
        vault = interface.ITheVault(address)
        strategies.append(vault.strategy())
        vaults_non_gac.append(vault.address) # V1.5 vaults don't have GAC

    # 4. Batch pause the vaults that don't have GAC, the strategies and infrastrcture contracts
    brownie.multicall(address="0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696")
    with brownie.multicall:
        # Batch pause vaults
        for vault in vaults_non_gac:
            GUARDIAN.pause(vault, {"from": dev})
        # Batch pause strats
        for strat in strategies:
            GUARDIAN.pause(strat, {"from": dev})
        # Pause badgerTree
        GUARDIAN.pause(REGISTRY.get("badgerTree"), {"from": dev})
        # Pause ibBTC Core
        ibBTC = interface.IibBTC(REGISTRY.get("ibBTC"))
        GUARDIAN.pause(ibBTC.core(), {"from": dev})

def Extract(lst):
    return [item[0] for item in lst]