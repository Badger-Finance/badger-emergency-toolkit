from brownie import interface
from helpers.addresses import r
from rich.console import Console
from tqdm import tqdm
from tabulate import tabulate

C = Console()

REGISTRY = interface.IBadgerRegistryV2(r.registry_v2)
GUARDIAN = interface.IWarRoomGatedProxy(REGISTRY.get("guardian"))
YEARN_VAULT = r.yearn_vaults.byvWBTC

VAULT_STATUS = [0, 1, 2, 3]

# Tables variables
tableHead = ["Name", "Address", "GAC Paused", "Local Paused"]
vaults_data = []
strategies_data = []
infra_data = []

def main():
    # 1. Is GAC paused?
    gac = interface.IGac(REGISTRY.get("globalAccessControl"))
    gac_status = gac.paused()

    # 2. Fetch all vaults from the Registry (V1, V1.5) for all status (deprecated, exp, guarded, open)
    C.print("[cyan]Fetching vaults and strategies from Registry...[/cyan]")
    vaults_v1 = []
    for status in tqdm(VAULT_STATUS):
        vaults_v1 += extract(REGISTRY.getFilteredProductionVaults("v1", status))

    vaults_v1_5 = []
    for status in tqdm(VAULT_STATUS):
        vaults_v1_5 += extract(REGISTRY.getFilteredProductionVaults("v1.5", status))

    # 3. Get pause status from all Vaults v1 and their strategies
    for address in vaults_v1:
        vault = interface.ISettV4h(address)
        # Check if GAC variable exists on vault
        try:
            vault.GAC()
            try:
                vaults_data.append([
                    vault.name(),
                    address,
                    gac_status,
                    vault.paused()
                ])
            except: # Some vaults can be globally paused but not locally
                vaults_data.append([
                    vault.name(),
                    address,
                    gac_status,
                    False
                ])
        except:
            try:
                vaults_data.append([
                    vault.name(),
                    address,
                    False,
                    vault.paused()
                ])
            except: # Some vaults can be globally paused but not locally
                vaults_data.append([
                    vault.name(),
                    address,
                    False,
                    False
                ])

        # Yearn vault doesn't contain controller/strategy
        if address != YEARN_VAULT:
            controller = interface.IController(vault.controller())
            strategy = interface.IStrategy(controller.strategies(vault.token()))
            try:
                strategies_data.append([
                    strategy.getName(),
                    strategy.address,
                    False, # Strategies don't have GAC
                    strategy.paused()
                ])
            except: # If strategy can't be paused
                strategies_data.append([
                    strategy.getName(),
                    strategy.address,
                    False, # Strategies don't have GAC
                    False
                ])

    # 4. Get pause status from all Vaults v1.5 and their strategies
    for address in vaults_v1_5:
        vault = interface.ITheVault(address)
        vaults_data.append([
            vault.name(),
            address,
            False, # There's no GAC on 
            vault.paused()
        ])

        strategy = interface.IStrategy(vault.strategy())
        strategies_data.append([
            strategy.getName(),
            strategy.address,
            False,
            strategy.paused()
        ])

    # 5. Get pause status from the infra contracts
    badgerTree = interface.IBadgerTreeV2(REGISTRY.get("badgerTree"))
    infra_data.append([
        "BadgerTree",
        badgerTree.address,
        False,
        badgerTree.paused()
    ])

    core = interface.ICore((interface.IibBTC(REGISTRY.get("ibBTC"))).core())
    infra_data.append([
        "IbBTC's Core",
        core.address,
        False,
        core.paused()
    ])

    # 6. Print tables
    C.print("\n[cyan]Vaults Pause Status[/cyan]\n")
    print(tabulate(vaults_data, tableHead, tablefmt="grid"))

    C.print("\n[cyan]Strategies Pause Status[/cyan]\n")
    print(tabulate(strategies_data, tableHead, tablefmt="grid"))

    C.print("\n[cyan]Infrastructure Pause Status[/cyan]\n")
    print(tabulate(infra_data, tableHead, tablefmt="grid"))




def extract(lst):
    return [item[0] for item in lst]