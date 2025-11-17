from Py4GWCoreLib import GLOBAL_CACHE
from Py4GWCoreLib import Timer
from Py4GWCoreLib import Utils
module_name = "Drop Unyielding Aura"

class config:
    def __init__(self):
        self.is_map_loading = False
        self.is_map_ready = False
        self.is_party_loaded = False
        self.is_explorable = False
        self.buff_exists = False
        self.map_valid = False
        
        self.game_throttle_time = 100
        self.game_throttle_timer = Timer()
        self.game_throttle_timer.Start()

widget_config = config()



def configure():
    pass

def main():
    global widget_config
    unyielding_aura = GLOBAL_CACHE.Skill.GetID("Unyielding_Aura")
    if widget_config.game_throttle_timer.HasElapsed(widget_config.game_throttle_time):
        widget_config.is_map_loading = GLOBAL_CACHE.Map.IsMapLoading()
        if widget_config.is_map_loading:
            return
        
        widget_config.is_map_ready = GLOBAL_CACHE.Map.IsMapReady()
        widget_config.is_party_loaded = GLOBAL_CACHE.Party.IsPartyLoaded()
        widget_config.is_explorable = GLOBAL_CACHE.Map.IsExplorable()
        widget_config.map_valid = widget_config.is_map_ready and widget_config.is_party_loaded and widget_config.is_explorable
        
        if widget_config.map_valid:
            player_id = GLOBAL_CACHE.Player.GetAgentID()
            widget_config.buff_exists = GLOBAL_CACHE.Effects.EffectExists(player_id, unyielding_aura) or GLOBAL_CACHE.Effects.BuffExists(player_id, unyielding_aura)
        widget_config.game_throttle_timer.Start()
        
    if widget_config.map_valid and widget_config.buff_exists:
        # Check if any party member is dead within earshot
        # Earshot range in Guild Wars is 1012 game units
        EARSHOT_RANGE = 1012
        party_member_dead_in_earshot = False
        
        player_id = GLOBAL_CACHE.Player.GetAgentID()
        player_x, player_y = GLOBAL_CACHE.Agent.GetXY(player_id)
        
        # Check heroes
        heroes = GLOBAL_CACHE.Party.GetHeroes()
        for hero in heroes:
            if hero.agent_id > 0 and GLOBAL_CACHE.Agent.IsDead(hero.agent_id):
                hero_x, hero_y = GLOBAL_CACHE.Agent.GetXY(hero.agent_id)
                distance = Utils.Distance((player_x, player_y), (hero_x, hero_y))
                if distance <= EARSHOT_RANGE:
                    party_member_dead_in_earshot = True
                    break
        
        # Check other players if no dead hero found yet
        if not party_member_dead_in_earshot:
            players = GLOBAL_CACHE.Party.GetPlayers()
            for player in players:
                player_agent_id = GLOBAL_CACHE.Party.Players.GetAgentIDByLoginNumber(player.login_number)
                # Skip self
                if player_agent_id == player_id or player_agent_id == 0:
                    continue
                if GLOBAL_CACHE.Agent.IsDead(player_agent_id):
                    other_player_x, other_player_y = GLOBAL_CACHE.Agent.GetXY(player_agent_id)
                    distance = Utils.Distance((player_x, player_y), (other_player_x, other_player_y))
                    if distance <= EARSHOT_RANGE:
                        party_member_dead_in_earshot = True
                        break
        
        # Drop the buff if someone is dead within earshot
        if party_member_dead_in_earshot:
            buff_id = GLOBAL_CACHE.Effects.GetBuffID(unyielding_aura)
            if buff_id > 0:
                GLOBAL_CACHE.Effects.DropBuff(buff_id)


        

if __name__ == "__main__":
    main()

