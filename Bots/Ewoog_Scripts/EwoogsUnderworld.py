from __future__ import annotations

from Py4GWCoreLib import (GLOBAL_CACHE, Routines, ModelID, Botting)


CHANTRY_OF_SECRETS= 393
UNDERWORLD= 72
UNDERWORLD_PATH = [ (-1155, 6630), (-793, 8849), (-1603, 10449), (-2763, 10052), (-4714, 11789), (-5781, 12764), (-6299, 10357), (-4809, 8067), (-6425, 6605), (-6943, 7123), (-7697, 2579), (-11903, 961), (-13211, 5371), (-15409, 7074), (-11922, 7625), (-11281, 8726), (-9466, 9650), (-11230, 6702), (-13949, 2162), (-12711, -353), (-10150, -226), (-9457, 1306), (-6159, 7938), (-3756, 13272), (-129, 13361), (1212, 10132), (3986, 7330), (5419, 8122), (5877, 10589), (8644, 12566), (8680, 17435), (5941, 18928), (8600, 21787), (11001, 19868), (13029, 20028), (13815, 16895), (13886, 13697), (12015, 14004), (10415, 17096), (7000, 15123), (3852, 5634), (224, 1423), (4439, -2468), (-3564, -5933), (981, -8881), (6530, -7815), (7917, -12613), (7053, -16861), (12976, -12223), (11642, -1828), (12602, 1636), (12037, 4314), (8622, 6020), (7341, 6944), (9271, 7024) ]

bot = Botting("Ewoog's Underworld",
              upkeep_birthday_cupcake_restock=10,
              upkeep_honeycomb_restock=20,
              upkeep_war_supplies_restock=2,
              upkeep_auto_inventory_management_active=False,
              upkeep_auto_combat_active=False,
              upkeep_auto_loot_active=True)


def create_bot_routine(bot: Botting) -> None:
    Chantry_of_Secrets(bot)
    Underworld(bot)


def Chantry_of_Secrets(bot: Botting) -> None:
    bot.States.AddHeader("CHANTRY_OF_SECRETS")
    bot.Templates.Routines.PrepareForFarm(map_id_to_travel=CHANTRY_OF_SECRETS)
    bot.Party.SetHardMode(False)
    bot.Move.XY(-8936.83, 3576.26, "go to Statue of Grenth")
    bot.States.AddCustomState(lambda: GLOBAL_CACHE.Player.SendChatCommand("kneel"), "kneel")
    bot.Wait.ForTime(6000)
    bot.Move.XYAndDialog(-8936.00, 3866.00, 0x85, "ask to enter")
    bot.Wait.ForMapToChange(72) # we are in the dungeon
    bot.Wait.ForTime(10000)

def Underworld(bot: Botting) -> None:
    bot.States.AddHeader("UNDERWORLD")
    bot.Templates.Multibox_Aggressive()
    #bot.States.AddManagedCoroutine("Upkeep Multibox Consumables", lambda: _upkeep_multibox_consumables(bot))
    bot.Move.XYAndDialog(281.00, 7229.00, 0x806501)
    bot.Move.FollowAutoPath(UNDERWORLD_PATH, "Kill Route")
    bot.Wait.UntilOutOfCombat()
    #bot.States.RemoveManagedCoroutine("Upkeep Multibox Consumables")
    bot.Multibox.ResignParty()
    bot.Wait.UntilOnOutpost()
    bot.Wait.ForTime(20000)
    bot.States.JumpToStepName("[H]CHANTRY_OF_SECRETS_1")

bot.SetMainRoutine(create_bot_routine)


def _upkeep_multibox_consumables(bot: "Botting"):
    while True:
        yield from bot.Wait._coro_for_time(15000)
        if not Routines.Checks.Map.MapValid():
            continue

        if Routines.Checks.Map.IsOutpost():
            continue

        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Essence_Of_Celerity.value,
                                                                 GLOBAL_CACHE.Skill.GetID(
                                                                     "Essence_of_Celerity_item_effect"), 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Grail_Of_Might.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Grail_of_Might_item_effect"),
                                                                 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Armor_Of_Salvation.value,
                                                                 GLOBAL_CACHE.Skill.GetID(
                                                                     "Armor_of_Salvation_item_effect"), 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Birthday_Cupcake.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Birthday_Cupcake_skill"), 0,
                                                                 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Golden_Egg.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Golden_Egg_skill"), 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Candy_Corn.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Candy_Corn_skill"), 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Candy_Apple.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Candy_Apple_skill"), 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Slice_Of_Pumpkin_Pie.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Pie_Induced_Ecstasy"), 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Drake_Kabob.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Drake_Skin"), 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Bowl_Of_Skalefin_Soup.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Skale_Vigor"), 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.Pahnai_Salad.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Pahnai_Salad_item_effect"),
                                                                 0, 0))
        yield from bot.helpers.Multibox._use_consumable_message((ModelID.War_Supplies.value,
                                                                 GLOBAL_CACHE.Skill.GetID("Well_Supplied"), 0, 0))
        for i in range(1, 5):
            GLOBAL_CACHE.Inventory.UseItem(ModelID.Honeycomb.value)
            yield from bot.Wait._coro_for_time(250)

def main():
    bot.Update()
    bot.UI.draw_window()

if __name__ == "__main__":
    main()
