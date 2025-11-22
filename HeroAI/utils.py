from Py4GWCoreLib import GLOBAL_CACHE, Allegiance, Overlay, Weapon
from .constants import MAX_NUM_PLAYERS
from .targeting import *
from .cache_data import CacheData
from .settings import Settings


def GetEffectiveLeaderID():
    """
    Get the agent ID of the effective leader for multibox purposes.
    If UseDesignatedLeader is enabled and the designated leader is in the party,
    returns their agent ID. Otherwise, returns the actual party leader's agent ID.
    """
    # Get designated leader settings from shared memory (shared across all accounts)
    use_designated_leader = GLOBAL_CACHE.ShMem.GetUseDesignatedLeader()
    designated_leader_email = GLOBAL_CACHE.ShMem.GetDesignatedLeaderEmail()
    
    # If designated leader feature is enabled and an email is set
    if use_designated_leader and designated_leader_email:
        # Try to find the designated leader in the party
        accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
        for account in accounts:
            if account.AccountEmail == designated_leader_email:
                # Check if they're in the same party
                own_account = GLOBAL_CACHE.ShMem.GetAccountDataFromEmail(GLOBAL_CACHE.Player.GetAccountEmail())
                if own_account and account.PartyID == own_account.PartyID:
                    return account.PlayerID
    
    # Fall back to actual party leader
    return GLOBAL_CACHE.Party.GetPartyLeaderID()


def DistanceFromLeader(cached_data:CacheData):
    return Utils.Distance(GLOBAL_CACHE.Agent.GetXY(GetEffectiveLeaderID()),GLOBAL_CACHE.Agent.GetXY(GLOBAL_CACHE.Player.GetAgentID()))

def DistanceFromWaypoint(posX,posY):
    distance = Utils.Distance((posX,posY), GLOBAL_CACHE.Player.GetXY())
    return distance if distance > 200 else 0


""" main configuration helpers """

def CheckForEffect(agent_id, skill_id):
    """this function needs to be expanded as more functionality is added"""
    import HeroAI.shared_memory_manager as shared_memory_manager
    shared_memory_handler = shared_memory_manager.SharedMemoryManager()   
    
    def _IsPartyMember(agent_id):
        for i in range(MAX_NUM_PLAYERS):
            player_data = shared_memory_handler.get_player(i)
            if player_data and player_data["IsActive"] and player_data["PlayerID"] == agent_id:
                return True
            
        allegiance , _ = GLOBAL_CACHE.Agent.GetAllegiance(agent_id)
        if allegiance == Allegiance.SpiritPet.value and not GLOBAL_CACHE.Agent.IsSpawned(agent_id):
            return True
        
        return False

    """
    allegiance , _ = Agent.GetAllegiance(agent_id)
    if allegiance == Allegiance.NpcMinipet.value:
        return True
    """
    result = False
    if _IsPartyMember(agent_id):
        player_buffs = shared_memory_handler.get_agent_buffs(agent_id)
        for buff in player_buffs:
            if buff == skill_id:
                result = True
    else:
        result = GLOBAL_CACHE.Effects.BuffExists(agent_id, skill_id) or GLOBAL_CACHE.Effects.EffectExists(agent_id, skill_id)
    
    return result

def IsHeroFlagged(cached_data:CacheData,index):
    if  index != 0 and index <= GLOBAL_CACHE.Party.GetHeroCount():
        return GLOBAL_CACHE.Party.Heroes.IsHeroFlagged(index)
    else:
        return cached_data.HeroAI_vars.all_player_struct[index-GLOBAL_CACHE.Party.GetHeroCount()].IsFlagged and cached_data.HeroAI_vars.all_player_struct[index-GLOBAL_CACHE.Party.GetHeroCount()].IsActive


def DrawFlagAll(pos_x, pos_y):
    pos_z = Overlay().FindZ(pos_x, pos_y)

    Overlay().BeginDraw()
    Overlay().DrawLine3D(pos_x, pos_y, pos_z, pos_x, pos_y, pos_z - 150, Utils.RGBToColor(0, 255, 0, 255), 3)
    Overlay().DrawTriangleFilled3D(
        pos_x, pos_y, pos_z - 150,               # Base point
        pos_x, pos_y, pos_z - 120,               # 30 units up
        pos_x - 50, pos_y, pos_z - 135,          # 50 units left, 15 units up
        Utils.RGBToColor(0, 255, 0, 255)
    )

    Overlay().EndDraw()


def DrawHeroFlag(pos_x, pos_y):
    pos_z = Overlay().FindZ(pos_x, pos_y)

    Overlay().BeginDraw()
    Overlay().DrawLine3D(pos_x, pos_y, pos_z, pos_x, pos_y, pos_z - 150, Utils.RGBToColor(0, 255, 0, 255), 3)
    Overlay().DrawTriangleFilled3D(
        pos_x + 25, pos_y, pos_z - 150,          # Right base
        pos_x - 25, pos_y, pos_z - 150,          # Left base
        pos_x, pos_y, pos_z - 100,               # 50 units up
        Utils.RGBToColor(0, 255, 0, 255)
    )
    Overlay().EndDraw()
